from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import CheckIn, MediaObject
from app.repositories.stores import get_store


ALLOWED_IMAGE_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def validate_check_in_image(content: bytes) -> tuple[str, str, int, int]:
    if not content:
        raise ApiError(400, "IMAGE_REQUIRED", "打卡必须上传一张图片", field="file")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "文件不是有效图片", field="file") from exc
    content_type = ALLOWED_IMAGE_TYPES.get(image_format)
    if content_type is None:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "仅支持 JPEG、PNG 或 WebP 图片", field="file")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    return content_type, extension, width, height


def check_in_view(item: CheckIn, storage: MinioStorage) -> dict:
    return {
        "id": str(item.id),
        "store_id": str(item.store_id),
        "photo_url": storage.public_object_url(item.photo.object_key),
        "note": item.note,
        "checked_at": item.checked_at,
        "created_at": item.created_at,
    }


async def create_check_in(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    user_id: int,
    store_id: int,
    content: bytes,
    original_filename: str,
    note: str | None,
) -> dict:
    if await get_store(session, store_id, active_only=True) is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    content_type, extension, width, height = validate_check_in_image(content)
    object_key = f"uploads/users/{user_id}/checkins/{uuid.uuid4().hex}.{extension}"
    await storage.put_bytes(object_key, content, content_type)
    try:
        media = MediaObject(
            bucket=storage.bucket,
            object_key=object_key,
            original_filename=original_filename or object_key,
            content_type=content_type,
            size_bytes=len(content),
            width=width,
            height=height,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            source_provider="user-upload",
            owner_user_id=user_id,
            purpose="checkin",
            upload_state="pending",
        )
        session.add(media)
        await session.flush()
        check_in = CheckIn(
            user_id=user_id,
            store_id=store_id,
            photo_media_id=media.id,
            note=note.strip() if note else None,
        )
        session.add(check_in)
        media.upload_state = "attached"
        await session.commit()
        await session.refresh(check_in)
        check_in.photo = media
        return check_in_view(check_in, storage)
    except Exception:
        await session.rollback()
        await storage.remove(object_key)
        raise


async def user_check_ins_page(
    session: AsyncSession,
    storage: MinioStorage,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    total = int((await session.scalar(select(func.count(CheckIn.id)).where(CheckIn.user_id == user_id))) or 0)
    query = (
        select(CheckIn)
        .where(CheckIn.user_id == user_id)
        .order_by(CheckIn.checked_at.desc(), CheckIn.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await session.scalars(query)).all())
    return [check_in_view(item, storage) for item in items], total
