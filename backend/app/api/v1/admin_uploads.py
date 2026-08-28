from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, Request, UploadFile
from PIL import Image, UnidentifiedImageError

from app.api.v1.utils import response
from app.core.dependencies import AdminDep, SessionDep, SettingsDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import MediaObject
from app.schemas.common import ApiResponse
from app.schemas.stores import ImageUploadData


router = APIRouter(prefix="/admin/uploads", tags=["Admin Uploads"])
ALLOWED_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@router.post("/images", response_model=ApiResponse[ImageUploadData], status_code=201)
async def upload_image(
    request: Request,
    admin: AdminDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "图片不能超过设定大小")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format or ""
            width, height = image.size
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "文件不是有效图片") from exc
    content_type = ALLOWED_TYPES.get(image_format.upper())
    if content_type is None:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "仅支持 JPEG、PNG 或 WebP")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    object_key = f"uploads/stores/{uuid.uuid4().hex}.{extension}"
    checksum = hashlib.sha256(content).hexdigest()
    await storage.put_bytes(object_key, content, content_type)
    try:
        media = MediaObject(
            bucket=storage.bucket,
            object_key=object_key,
            original_filename=file.filename or object_key,
            content_type=content_type,
            size_bytes=len(content),
            width=width,
            height=height,
            checksum_sha256=checksum,
            source_provider="admin-upload",
        )
        session.add(media)
        await session.commit()
    except Exception:
        await session.rollback()
        await storage.remove(object_key)
        raise
    return response(request, {"url": storage.public_object_url(object_key), "content_type": content_type, "size": len(content)})
