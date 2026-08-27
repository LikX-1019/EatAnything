from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import SessionDep, SettingsDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.schemas.checkins import CheckInItem
from app.schemas.common import ApiResponse, PageData
from app.services.checkins import create_check_in, update_check_in, user_check_ins_page
from app.models import CheckIn


router = APIRouter(tags=["Check-ins"])


@router.post("/stores/{storeId}/check-ins", response_model=ApiResponse[CheckInItem], status_code=201)
async def add_check_in(
    storeId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    note: str | None = Form(default=None, max_length=500),
    storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "图片不能超过设定大小", field="file")
    data = await create_check_in(
        session,
        storage,
        user_id=user.id,
        store_id=parse_store_id(storeId),
        content=content,
        original_filename=file.filename or "checkin-image",
        note=note,
    )
    return response(request, data)


@router.get("/me/check-ins", response_model=ApiResponse[PageData[CheckInItem]])
async def list_my_check_ins(
    request: Request,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await user_check_ins_page(session, storage, user.id, page=page, page_size=page_size)
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


async def _edit_check_in_impl(
    checkInId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile | None = File(default=None),
    note: str | None = Form(default=None, max_length=500),
    storage: MinioStorage = Depends(get_minio),
):
    try:
        check_in_id = int(checkInId)
    except ValueError as exc:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡记录不存在") from exc
    content = None
    filename = None
    if file is not None:
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise ApiError(413, "FILE_TOO_LARGE", "图片不能超过设定大小", field="file")
        filename = file.filename or "checkin-image"
    data = await update_check_in(
        session,
        storage,
        user_id=user.id,
        check_in_id=check_in_id,
        content=content,
        original_filename=filename,
        note=note,
    )
    return response(request, data)


@router.patch("/me/check-ins/{checkInId}", response_model=ApiResponse[CheckInItem])
async def edit_check_in(
    checkInId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile | None = File(default=None),
    note: str | None = Form(default=None, max_length=500),
    storage: MinioStorage = Depends(get_minio),
):
    return await _edit_check_in_impl(checkInId, request, user, session, settings, file, note, storage)


@router.post("/me/check-ins/{checkInId}", include_in_schema=False)
async def edit_check_in_upload(
    checkInId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile | None = File(default=None),
    note: str | None = Form(default=None, max_length=500),
    storage: MinioStorage = Depends(get_minio),
):
    # uni.uploadFile 在小程序端固定使用 POST，保留兼容入口并复用同一更新逻辑。
    return await _edit_check_in_impl(checkInId, request, user, session, settings, file, note, storage)


@router.get("/me/check-ins/{checkInId}/photo", include_in_schema=False)
async def get_my_check_in_photo(
    checkInId: str,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
):
    try:
        check_in_id = int(checkInId)
    except ValueError as exc:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡记录不存在") from exc
    check_in = await session.get(CheckIn, check_in_id)
    if check_in is None or check_in.user_id != user.id or check_in.status != "published":
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡记录不存在")
    try:
        content, content_type = await storage.get_bytes(check_in.photo.object_key, bucket=storage.private_bucket)
    except Exception as exc:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡照片不存在") from exc
    return Response(content=content, media_type=content_type or "application/octet-stream", headers={"Cache-Control": "private, max-age=60"})
