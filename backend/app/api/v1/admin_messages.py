from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import and_, func, or_, select

from app.api.v1.utils import response
from app.core.dependencies import AdminDep, SessionDep, SettingsDep, get_minio
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import AppUser, MediaObject, MessageMediaLink, PlatformMessage, School, Store, UserWechatSubscription
from app.schemas.messages import MessageAdminCreate, MessageAdminUpdate
from app.services.admin_scope import admin_school_ids, ensure_school_allowed, is_platform_admin
from app.services.messages import delivery_counts, message_view, replace_message_media, sanitize_message_html, validate_action
from app.services.moderation import add_audit_log


router = APIRouter(prefix="/admin/messages", tags=["Admin Messages"])
ALLOWED_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


async def ensure_target_allowed(session: SessionDep, admin, target_type: str, school_id: int | None, user_id: int | None) -> AppUser | None:
    if target_type == "all":
        if not is_platform_admin(admin):
            raise ApiError(403, "FORBIDDEN", "只有平台管理员可以发送全平台消息")
        if school_id or user_id:
            raise ApiError(422, "INVALID_MESSAGE_TARGET", "全平台消息不能指定学校或用户")
        return None
    if target_type == "school":
        if not school_id or user_id:
            raise ApiError(422, "INVALID_MESSAGE_TARGET", "学校消息必须且只能指定学校")
        await ensure_school_allowed(session, admin, school_id)
        if await session.get(School, school_id) is None:
            raise ApiError(404, "SCHOOL_NOT_FOUND", "目标学校不存在")
        return None
    if not user_id or school_id:
        raise ApiError(422, "INVALID_MESSAGE_TARGET", "个人消息必须且只能指定用户")
    user = await session.get(AppUser, user_id)
    if user is None:
        raise ApiError(404, "USER_NOT_FOUND", "目标用户不存在")
    if user.school_id:
        await ensure_school_allowed(session, admin, user.school_id)
    elif not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "无权向未选择学校的用户发送消息")
    return user


async def ensure_action_allowed(session: SessionDep, admin, action_type: str | None, action_target_id: int | None) -> None:
    validate_action(action_type, action_target_id)
    if action_type != "store_detail" or action_target_id is None:
        return
    store = await session.get(Store, action_target_id)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "跳转目标店铺不存在")
    await ensure_school_allowed(session, admin, store.school_id)


async def recipient_estimate(session: SessionDep, item: PlatformMessage) -> dict:
    filters = []
    if item.target_type == "all":
        filters.append(AppUser.status == "active")
    elif item.target_type == "school":
        filters.extend((AppUser.status == "active", AppUser.school_id == item.school_id))
    else:
        filters.append(AppUser.id == item.user_id)
    in_app = int((await session.scalar(select(func.count(AppUser.id)).where(*filters))) or 0)
    wechat = int((await session.scalar(
        select(func.count(UserWechatSubscription.user_id)).join(
            AppUser, AppUser.id == UserWechatSubscription.user_id
        ).where(*filters, UserWechatSubscription.template_kind == item.kind,
                UserWechatSubscription.enabled.is_(True), UserWechatSubscription.status == "accepted")
    )) or 0)
    return {"in_app": in_app, "wechat": wechat}


async def get_admin_message(session: SessionDep, admin, message_id: int) -> PlatformMessage:
    item = await session.get(PlatformMessage, message_id)
    if item is None:
        raise ApiError(404, "MESSAGE_NOT_FOUND", "消息不存在")
    if item.target_type == "all" and not is_platform_admin(admin):
        raise ApiError(403, "FORBIDDEN", "无权管理该消息")
    if item.target_type == "school" and item.school_id:
        await ensure_school_allowed(session, admin, item.school_id)
    if item.target_type == "user" and item.user_id:
        await ensure_target_allowed(session, admin, "user", item.school_id, item.user_id)
    return item


@router.get("")
async def list_messages(
    request: Request, admin: AdminDep, session: SessionDep,
    kind: str | None = Query(default=None, pattern="^(notification|announcement)$"),
    status: str | None = Query(default=None, pattern="^(draft|published|revoked)$"),
    school_id: int | None = Query(default=None, gt=0), page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    scope = await admin_school_ids(session, admin)
    filters = []
    if scope is not None:
        filters.append(or_(
            and_(PlatformMessage.target_type == "school", PlatformMessage.school_id.in_(scope or {-1})),
            and_(PlatformMessage.target_type == "user", PlatformMessage.user_id.in_(
                select(AppUser.id).where(AppUser.school_id.in_(scope or {-1}))
            )),
        ))
    if school_id:
        await ensure_school_allowed(session, admin, school_id)
        filters.append(or_(PlatformMessage.school_id == school_id, PlatformMessage.user_id.in_(
            select(AppUser.id).where(AppUser.school_id == school_id)
        )))
    if kind:
        filters.append(PlatformMessage.kind == kind)
    if status:
        filters.append(PlatformMessage.status == status)
    total = int((await session.scalar(select(func.count(PlatformMessage.id)).where(*filters))) or 0)
    rows = list((await session.scalars(select(PlatformMessage).where(*filters).order_by(
        PlatformMessage.created_at.desc(), PlatformMessage.id.desc()
    ).offset((page - 1) * page_size).limit(page_size))).all())
    return response(request, {"items": [message_view(item, include_admin=True) for item in rows], "page": page, "page_size": page_size, "total": total})


@router.post("", status_code=201)
async def create_message(payload: MessageAdminCreate, request: Request, admin: AdminDep, session: SessionDep, settings: SettingsDep):
    await ensure_target_allowed(session, admin, payload.target_type, payload.school_id, payload.user_id)
    await ensure_action_allowed(session, admin, payload.action_type, payload.action_target_id)
    item = PlatformMessage(
        kind=payload.kind, source="admin", title=payload.title.strip(),
        body_html=sanitize_message_html(payload.body_html, settings), target_type=payload.target_type,
        school_id=payload.school_id, user_id=payload.user_id, priority=payload.priority, status="draft",
        action_type=payload.action_type, action_target_id=payload.action_target_id,
        wechat_push=payload.wechat_push, publish_at=payload.publish_at, expire_at=payload.expire_at,
        created_by=admin.id, updated_by=admin.id,
    )
    session.add(item)
    await session.flush()
    await replace_message_media(session, item.id, payload.media_ids, body_html=item.body_html, settings=settings)
    add_audit_log(session, request, admin, action="message.create", target_type="platform_message", target_id=item.id, school_id=item.school_id, after={"kind": item.kind, "targetType": item.target_type})
    await session.commit()
    return response(request, {**message_view(item, include_admin=True), "estimate": await recipient_estimate(session, item)})


@router.get("/{messageId}")
async def message_detail(messageId: int, request: Request, admin: AdminDep, session: SessionDep):
    item = await get_admin_message(session, admin, messageId)
    media_ids = [str(value) for value in (await session.scalars(
        select(MessageMediaLink.media_id).where(MessageMediaLink.message_id == item.id)
    )).all()]
    return response(request, {**message_view(item, include_admin=True, delivery=await delivery_counts(session, item.id)), "media_ids": media_ids, "estimate": await recipient_estimate(session, item)})


@router.patch("/{messageId}")
async def update_message(messageId: int, payload: MessageAdminUpdate, request: Request, admin: AdminDep, session: SessionDep, settings: SettingsDep):
    item = await get_admin_message(session, admin, messageId)
    now = datetime.now(UTC)
    if item.status != "draft" and (not item.publish_at or item.publish_at <= now):
        raise ApiError(409, "MESSAGE_ALREADY_ACTIVE", "消息生效后不能编辑，请撤回后新建")
    values = payload.model_dump(exclude_unset=True, exclude={"media_ids"})
    target_type = values.get("target_type", item.target_type)
    school_id = values.get("school_id", item.school_id)
    user_id = values.get("user_id", item.user_id)
    await ensure_target_allowed(session, admin, target_type, school_id, user_id)
    action_type = values.get("action_type", item.action_type)
    action_target_id = values.get("action_target_id", item.action_target_id)
    await ensure_action_allowed(session, admin, action_type, action_target_id)
    publish_at = values.get("publish_at", item.publish_at)
    expire_at = values.get("expire_at", item.expire_at)
    if expire_at and publish_at and expire_at <= publish_at:
        raise ApiError(422, "INVALID_MESSAGE_EXPIRY", "失效时间必须晚于发布时间", field="expireAt")
    before = {"title": item.title, "targetType": item.target_type, "status": item.status}
    for key, value in values.items():
        if key == "body_html" and value is not None:
            value = sanitize_message_html(value, settings)
        if key == "title" and value is not None:
            value = value.strip()
        setattr(item, key, value)
    item.updated_by = admin.id
    item.updated_at = now
    if payload.media_ids is not None:
        await replace_message_media(session, item.id, payload.media_ids, body_html=item.body_html, settings=settings)
    elif payload.body_html is not None:
        existing_media_ids = list((await session.scalars(
            select(MessageMediaLink.media_id).where(MessageMediaLink.message_id == item.id)
        )).all())
        await replace_message_media(session, item.id, existing_media_ids, body_html=item.body_html, settings=settings)
    add_audit_log(session, request, admin, action="message.update", target_type="platform_message", target_id=item.id, school_id=item.school_id, before=before, after={"title": item.title, "targetType": item.target_type, "status": item.status})
    await session.commit()
    return response(request, message_view(item, include_admin=True))


@router.post("/{messageId}/publish")
async def publish_message(messageId: int, request: Request, admin: AdminDep, session: SessionDep):
    item = await get_admin_message(session, admin, messageId)
    if item.status == "revoked":
        raise ApiError(409, "MESSAGE_REVOKED", "已撤回消息不能再次发布")
    now = datetime.now(UTC)
    item.status = "published"
    item.publish_at = item.publish_at or now
    if item.expire_at and item.expire_at <= now:
        raise ApiError(422, "INVALID_MESSAGE_EXPIRY", "失效时间必须晚于当前时间", field="expireAt")
    item.published_at = now
    item.updated_by = admin.id
    item.updated_at = now
    add_audit_log(session, request, admin, action="message.publish", target_type="platform_message", target_id=item.id, school_id=item.school_id, after={"publishAt": item.publish_at, "wechatPush": item.wechat_push})
    await session.commit()
    return response(request, {**message_view(item, include_admin=True), "estimate": await recipient_estimate(session, item)})


@router.post("/{messageId}/revoke")
async def revoke_message(messageId: int, request: Request, admin: AdminDep, session: SessionDep):
    item = await get_admin_message(session, admin, messageId)
    if item.status != "published":
        raise ApiError(409, "MESSAGE_NOT_PUBLISHED", "只有已发布消息可以撤回")
    item.status = "revoked"
    item.revoked_at = datetime.now(UTC)
    item.updated_by = admin.id
    add_audit_log(session, request, admin, action="message.revoke", target_type="platform_message", target_id=item.id, school_id=item.school_id)
    await session.commit()
    return response(request, message_view(item, include_admin=True))


@router.post("/images", status_code=201)
async def upload_message_image(
    request: Request, admin: AdminDep, session: SessionDep, settings: SettingsDep,
    file: UploadFile = File(...), storage: MinioStorage = Depends(get_minio),
):
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "图片不能超过设定大小")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format, width, height = (image.format or "").upper(), *image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "文件不是有效图片") from exc
    content_type = ALLOWED_TYPES.get(image_format)
    if not content_type:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "仅支持 JPEG、PNG 或 WebP")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    object_key = f"uploads/messages/{uuid.uuid4().hex}.{extension}"
    await storage.put_bytes(object_key, content, content_type)
    try:
        media = MediaObject(
            bucket=storage.bucket, object_key=object_key, original_filename=file.filename or object_key,
            content_type=content_type, size_bytes=len(content), width=width, height=height,
            checksum_sha256=hashlib.sha256(content).hexdigest(), source_provider="admin-upload",
            purpose="message_content", upload_state="attached",
        )
        session.add(media)
        await session.commit()
    except Exception:
        await session.rollback()
        await storage.remove(object_key)
        raise
    return response(request, {"media_id": str(media.id), "url": storage.public_object_url(object_key), "content_type": content_type, "size": len(content)})
