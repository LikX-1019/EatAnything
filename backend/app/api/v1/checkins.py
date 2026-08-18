from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.v1.utils import response, store_id as parse_store_id
from app.core.dependencies import SessionDep, SettingsDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.schemas.checkins import CheckInItem
from app.schemas.common import ApiResponse, PageData
from app.services.checkins import create_check_in, user_check_ins_page


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
