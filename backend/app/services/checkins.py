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
from app.services.moderation import ensure_user_can_upload_image


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
    updated_at = getattr(item, "updated_at", None) or getattr(item, "checked_at", None)
    cache_suffix = f"?v={int(updated_at.timestamp() * 1000)}" if updated_at is not None else ""
    return {
        "id": str(item.id),
        "store_id": str(item.store_id),
        # 私有媒体只通过带鉴权的 API 读取，不返回 MinIO 公网地址。
        "photo_url": (
            f"/api/v1/me/check-ins/{item.id}/photo{cache_suffix}"
            if hasattr(storage, "private_bucket")
            else storage.public_object_url(item.photo.object_key)
        ),
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
    await ensure_user_can_upload_image(session, user_id)
    store = await get_store(session, store_id, active_only=True)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    content_type, extension, width, height = validate_check_in_image(content)
    object_key = f"uploads/users/{user_id}/checkins/{uuid.uuid4().hex}.{extension}"
    private_bucket = getattr(storage, "private_bucket", storage.bucket)
    if hasattr(storage, "private_bucket"):
        await storage.put_bytes(object_key, content, content_type, bucket=private_bucket)
    else:
        # 兼容只实现旧接口的测试替身；真实 MinioStorage 始终使用私有 bucket。
        await storage.put_bytes(object_key, content, content_type)
    try:
        media = MediaObject(
            bucket=private_bucket,
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
            school_id=store.school_id,
            photo_media_id=media.id,
            note=note.strip() if note else None,
            status="published",
        )
        session.add(check_in)
        media.upload_state = "attached"
        await session.commit()
        await session.refresh(check_in)
        check_in.photo = media
        return check_in_view(check_in, storage)
    except Exception:
        await session.rollback()
        if hasattr(storage, "private_bucket"):
            await storage.remove(object_key, bucket=private_bucket)
        else:
            await storage.remove(object_key)
        raise


async def update_check_in(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    user_id: int,
    check_in_id: int,
    content: bytes | None,
    original_filename: str | None,
    note: str | None,
) -> dict:
    check_in = await session.scalar(
        select(CheckIn).where(CheckIn.id == check_in_id, CheckIn.user_id == user_id)
    )
    if check_in is None:
        raise ApiError(404, "CHECK_IN_NOT_FOUND", "打卡记录不存在")

    if content is not None:
        await ensure_user_can_upload_image(session, user_id)

    old_object_key = check_in.photo.object_key
    new_object_key: str | None = None
    private_bucket = getattr(storage, "private_bucket", storage.bucket)
    try:
        if content is not None:
            content_type, extension, width, height = validate_check_in_image(content)
            new_object_key = f"uploads/users/{user_id}/checkins/{uuid.uuid4().hex}.{extension}"
            if hasattr(storage, "private_bucket"):
                await storage.put_bytes(new_object_key, content, content_type, bucket=private_bucket)
            else:
                await storage.put_bytes(new_object_key, content, content_type)
            media = check_in.photo
            media.bucket = private_bucket
            media.object_key = new_object_key
            media.original_filename = original_filename or new_object_key
            media.content_type = content_type
            media.size_bytes = len(content)
            media.width = width
            media.height = height
            media.checksum_sha256 = hashlib.sha256(content).hexdigest()

        check_in.note = note.strip() if note and note.strip() else None
        await session.commit()
        await session.refresh(check_in)
        if new_object_key and old_object_key != new_object_key:
            try:
                if hasattr(storage, "private_bucket"):
                    await storage.remove(old_object_key, bucket=private_bucket)
                else:
                    await storage.remove(old_object_key)
            except Exception:
                # 新图片已经关联成功，旧文件清理失败不应影响用户看到最新记录。
                pass
        return check_in_view(check_in, storage)
    except Exception:
        await session.rollback()
        if new_object_key:
            try:
                if hasattr(storage, "private_bucket"):
                    await storage.remove(new_object_key, bucket=private_bucket)
                else:
                    await storage.remove(new_object_key)
            except Exception:
                pass
        raise


async def user_check_ins_page(
    session: AsyncSession,
    storage: MinioStorage,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    filters = (CheckIn.user_id == user_id, CheckIn.status == "published")
    total = int((await session.scalar(select(func.count(CheckIn.id)).where(*filters))) or 0)
    query = (
        select(CheckIn)
        .where(*filters)
        .order_by(CheckIn.checked_at.desc(), CheckIn.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await session.scalars(query)).all())
    return [check_in_view(item, storage) for item in items], total
