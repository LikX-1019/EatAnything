from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import AdminDep, SessionDep, SettingsDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.repositories.stores import count_stores, get_store, list_stores
from app.schemas.common import ApiResponse, PageData
from app.schemas.stores import AdminStore, AdminStoreCreateRequest, AdminStoreUpdateRequest, StoreImportData
from app.services.import_stores import import_stores
from app.services.stores import admin_store_view, create_admin_store, update_admin_store


router = APIRouter(prefix="/admin/stores", tags=["Admin Stores"])


@router.get("", response_model=ApiResponse[PageData[AdminStore]])
async def list_admin_stores(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    keyword: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, pattern="^(active|hidden|closed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    storage: MinioStorage = Depends(get_minio),
):
    items = await list_stores(session, active_only=False, keyword=keyword, status=status, page=page, page_size=page_size)
    total = await count_stores(session, active_only=False, keyword=keyword, status=status)
    data = [await admin_store_view(session, storage, store) for store in items]
    return response(request, {"items": data, "page": page, "page_size": page_size, "total": total})


@router.post("", response_model=ApiResponse[AdminStore], status_code=201)
async def create_store(payload: AdminStoreCreateRequest, request: Request, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    data = await create_admin_store(session, storage, payload)
    return response(request, data)


@router.post("/import", response_model=ApiResponse[StoreImportData])
async def import_store_file(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    data = await import_stores(session, storage, settings, content, file.filename or "")
    return response(request, data)


@router.get("/{storeId}", response_model=ApiResponse[AdminStore])
async def get_admin_store(storeId: str, request: Request, admin: AdminDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    store = await get_store(session, parse_store_id(storeId), active_only=False)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
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
    return response(request, await update_admin_store(session, storage, store, payload))


@router.delete("/{storeId}", status_code=204)
async def archive_store(storeId: str, admin: AdminDep, session: SessionDep, version: int = Query(..., ge=1)):
    store = await get_store(
        session,
        parse_store_id(storeId),
        active_only=False,
        for_update=True,
    )
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在")
    if store.version != version:
        raise ApiError(409, "RESOURCE_VERSION_CONFLICT", "数据已被其他管理员修改，请刷新后重试")
    store.status = "closed"
    store.version += 1
    await session.commit()
    return None
