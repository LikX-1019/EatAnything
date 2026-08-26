from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import select

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import AdminDep, SessionDep, SettingsDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.repositories.stores import count_stores, get_store, list_stores
from app.models import School, SchoolArea
from app.schemas.common import ApiResponse, PageData
from app.schemas.stores import AdminStore, AdminStoreCreateRequest, AdminStoreUpdateRequest, StoreImportData
from app.services.import_stores import import_stores
from app.services.stores import admin_store_view, create_admin_store, update_admin_store
from app.services.admin_scope import admin_school_ids, ensure_school_allowed, scoped_school_id
from app.services.moderation import add_audit_log


router = APIRouter(prefix="/admin/stores", tags=["Admin Stores"])


@router.get("/options")
async def store_options(request: Request, admin: AdminDep, session: SessionDep):
    scope = await admin_school_ids(session, admin)
    school_query = select(School).where(School.status == "active")
    area_query = select(SchoolArea).where(SchoolArea.status == "active")
    if scope is not None:
        school_query = school_query.where(School.id.in_(scope or {-1}))
        area_query = area_query.where(SchoolArea.school_id.in_(scope or {-1}))
    schools = list((await session.scalars(school_query.order_by(School.name))).all())
    areas = list((await session.scalars(area_query.order_by(SchoolArea.school_id, SchoolArea.sort_order, SchoolArea.name))).all())
    grouped: dict[int, list[dict[str, object]]] = {}
    for area in areas:
        grouped.setdefault(area.school_id, []).append({"id": str(area.id), "areaCode": area.area_code, "name": area.name})
    return response(request, {"schools": [{"id": str(school.id), "schoolCode": school.school_code, "name": school.name, "areas": grouped.get(school.id, [])} for school in schools]})


@router.get("", response_model=ApiResponse[PageData[AdminStore]])
async def list_admin_stores(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    keyword: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, pattern="^(active|hidden|closed)$"),
    school_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    storage: MinioStorage = Depends(get_minio),
):
    selected_school_id = await scoped_school_id(session, admin, school_id)
    scope = await admin_school_ids(session, admin)
    allowed_school_ids = scope if selected_school_id is None else None
    items = await list_stores(session, active_only=False, keyword=keyword, status=status, page=page, page_size=page_size, school_id=selected_school_id, school_ids=allowed_school_ids)
    total = await count_stores(session, active_only=False, keyword=keyword, status=status, school_id=selected_school_id, school_ids=allowed_school_ids)
    data = [await admin_store_view(session, storage, store) for store in items]
    return response(request, {"items": data, "page": page, "page_size": page_size, "total": total})


@router.post("", response_model=ApiResponse[AdminStore], status_code=201)
async def create_store(payload: AdminStoreCreateRequest, request: Request, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    await ensure_school_allowed(session, admin, payload.school_id)
    data = await create_admin_store(session, storage, payload)
    add_audit_log(session, request, admin, action="store.create", target_type="store", target_id=data["id"], school_id=payload.school_id, after={"name": data["name"], "status": data["status"]})
    await session.commit()
    return response(request, data)


@router.post("/import", response_model=ApiResponse[StoreImportData])
async def import_store_file(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    school_id: int | None = Form(default=None),
    storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    if school_id is not None:
        await ensure_school_allowed(session, admin, school_id)
    data = await import_stores(session, storage, settings, content, file.filename or "", allowed_school_ids=await admin_school_ids(session, admin), target_school_id=school_id)
    add_audit_log(session, request, admin, action="store.import", target_type="store_import", target_id=file.filename or "upload", reason=f"新增 {data['created_count']}，更新 {data['updated_count']}", after={"totalRows": data["total_rows"]})
    await session.commit()
    return response(request, data)


@router.get("/{storeId}", response_model=ApiResponse[AdminStore])
async def get_admin_store(storeId: str, request: Request, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    store = await get_store(session, parse_store_id(storeId), active_only=False)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
    await ensure_school_allowed(session, admin, store.school_id)
    return response(request, await admin_store_view(session, storage, store))


@router.patch("/{storeId}", response_model=ApiResponse[AdminStore])
async def update_store(storeId: str, payload: AdminStoreUpdateRequest, request: Request, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    store = await get_store(
        session,
        parse_store_id(storeId),
        active_only=False,
        for_update=True,
    )
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
    await ensure_school_allowed(session, admin, store.school_id)
    if payload.school_id is not None:
        await ensure_school_allowed(session, admin, payload.school_id)
    before = {"name": store.name, "status": store.status, "version": store.version}
    data = await update_admin_store(session, storage, store, payload)
    add_audit_log(session, request, admin, action="store.update", target_type="store", target_id=store.id, school_id=store.school_id, before=before, after={"name": store.name, "status": store.status, "version": store.version})
    await session.commit()
    return response(request, data)


@router.delete("/{storeId}", status_code=204)
async def archive_store(storeId: str, request: Request, admin: AdminDep, session: SessionDep, version: int = Query(..., ge=1)):
    store = await get_store(
        session,
        parse_store_id(storeId),
        active_only=False,
        for_update=True,
    )
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
    await ensure_school_allowed(session, admin, store.school_id)
    if store.version != version:
        raise ApiError(409, "RESOURCE_VERSION_CONFLICT", "数据已被其他管理员修改，请刷新后重试")
    store.status = "closed"
    store.version += 1
    add_audit_log(session, request, admin, action="store.close", target_type="store", target_id=store.id, school_id=store.school_id, before={"status": "active"}, after={"status": "closed"})
    await session.commit()
    return None
