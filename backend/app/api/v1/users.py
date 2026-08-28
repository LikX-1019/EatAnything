from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, Request
from fastapi import File, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from app.api.v1.utils import response, school_id as parse_school_id
from app.core.dependencies import SessionDep, SettingsDep, UserDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import MediaObject, School
from app.schemas.common import ApiResponse
from app.schemas.users import AvatarUploadData, ProfileUpdate, SchoolSummary, UserProfile
from app.services.users import profile


router = APIRouter(tags=["User"])
ALLOWED_AVATAR_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@router.get("/me", response_model=ApiResponse[UserProfile])
async def current_user(request: Request, user: UserDep, session: SessionDep, storage: MinioStorage = Depends(get_minio)):
    data = await profile(session, storage, user)
    return {"data": data, "request_id": request.state.request_id}


@router.get("/schools", response_model=ApiResponse[list[SchoolSummary]])
async def list_schools(request: Request, user: UserDep, session: SessionDep):
    schools = list((await session.scalars(select(School).where(School.status == "active").order_by(School.name))).all())
    data = [
        {
            "id": str(school.id),
            "school_code": school.school_code,
            "name": school.name,
            "city": school.city,
            "district": school.district,
            "address": school.address,
        }
        for school in schools
    ]
    return response(request, data)


@router.put("/me/school/{schoolId}", response_model=ApiResponse[UserProfile])
async def select_school(
    schoolId: str,
    request: Request,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
):
    school_id = parse_school_id(schoolId)
    school = await session.scalar(select(School).where(School.id == school_id, School.status == "active"))
    if school is None:
        raise ApiError(404, "SCHOOL_NOT_FOUND", "学校不存在或已不可用")
    user.school_id = school.id
    await session.commit()
    await session.refresh(user)
    return response(request, await profile(session, storage, user))


@router.put("/me/profile", response_model=ApiResponse[UserProfile])
async def update_me_profile(
    payload: ProfileUpdate,
    request: Request,
    user: UserDep,
    session: SessionDep,
    storage: MinioStorage = Depends(get_minio),
):
    updates = payload.model_dump(exclude_unset=True)
    if "nickname" in updates:
        user.nickname = updates["nickname"]
    if "slogan" in updates:
        user.slogan = updates["slogan"]
    if "gender" in updates:
        user.gender = updates["gender"]
    if "birthday" in updates:
        user.birthday = updates["birthday"]
    await session.commit()
    await session.refresh(user)
    return response(request, await profile(session, storage, user))


@router.post("/me/avatar", response_model=ApiResponse[AvatarUploadData], status_code=201)
async def upload_me_avatar(
    request: Request,
    user: UserDep,
    session: SessionDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "图片不能超过设定大小", field="file")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format or ""
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "文件不是有效图片") from exc
    content_type = ALLOWED_AVATAR_TYPES.get(image_format.upper())
    if content_type is None:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "仅支持 JPEG、PNG 或 WebP")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    object_key = f"uploads/avatars/{uuid.uuid4().hex}.{extension}"
    checksum = hashlib.sha256(content).hexdigest()
    await storage.put_bytes(object_key, content, content_type)
    old_media_id = user.avatar_media_id
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
            source_provider="user-upload",
            owner_user_id=user.id,
            purpose="avatar",
            upload_state="attached",
        )
        session.add(media)
        await session.flush()
        user.avatar_media_id = media.id
        await session.commit()
        await session.refresh(user)
    except Exception:
        await session.rollback()
        await storage.remove(object_key)
        raise
    if old_media_id is not None:
        old = await session.get(MediaObject, old_media_id)
        if old is not None:
            await storage.remove(old.object_key, bucket=old.bucket)
            await session.delete(old)
            await session.commit()
    return response(request, {"avatar_url": storage.public_object_url(object_key)})
