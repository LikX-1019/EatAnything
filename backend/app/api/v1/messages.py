from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from sqlalchemy import case, select

from app.api.v1.utils import response
from app.core.dependencies import SessionDep, SettingsDep, UserDep
from app.core.errors import ApiError
from app.models import PlatformMessage, UserWechatSubscription
from app.schemas.messages import NotificationSettingsUpdate, WechatConsentRequest
from app.services.messages import (
    effective_message_filter,
    get_user_message,
    list_user_messages,
    mark_read,
    message_view,
    subscription_settings,
    unread_count,
)


router = APIRouter(prefix="/me", tags=["Messages"])
MESSAGE_KINDS = {"notification", "announcement"}


def parse_message_id(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ApiError(404, "MESSAGE_NOT_FOUND", "消息不存在") from exc
    if result <= 0:
        raise ApiError(404, "MESSAGE_NOT_FOUND", "消息不存在")
    return result


def normalize_message_kind(value: str | None) -> str | None:
    # 兼容旧版小程序把“全部”的空值序列化为 kind=。
    if value in {None, ""}:
        return None
    if value not in MESSAGE_KINDS:
        raise ApiError(400, "INVALID_ARGUMENT", "kind 必须是 notification 或 announcement", field="kind")
    return value


@router.get("/messages")
async def messages(
    request: Request, user: UserDep, session: SessionDep,
    kind: str | None = Query(default=None),
    unread_only: bool = False, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
):
    items, total = await list_user_messages(
        session,
        user,
        kind=normalize_message_kind(kind),
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    return response(request, {"items": items, "page": page, "page_size": page_size, "total": total})


@router.get("/messages/unread-count")
async def messages_unread_count(request: Request, user: UserDep, session: SessionDep):
    return response(request, {"count": await unread_count(session, user)})


@router.get("/messages/{messageId}")
async def message_detail(messageId: str, request: Request, user: UserDep, session: SessionDep):
    item, is_read = await get_user_message(session, user, parse_message_id(messageId))
    return response(request, message_view(item, is_read=is_read))


@router.post("/messages/{messageId}/read")
async def read_message(messageId: str, request: Request, user: UserDep, session: SessionDep):
    item, _ = await get_user_message(session, user, parse_message_id(messageId))
    await mark_read(session, user.id, [item.id])
    return response(request, {"id": str(item.id), "is_read": True})


@router.post("/messages/read-all")
async def read_all_messages(
    request: Request, user: UserDep, session: SessionDep,
    kind: str | None = Query(default=None),
):
    kind = normalize_message_kind(kind)
    query = select(PlatformMessage.id).where(effective_message_filter(user))
    if kind:
        query = query.where(PlatformMessage.kind == kind)
    ids = list((await session.scalars(query)).all())
    await mark_read(session, user.id, ids)
    return response(request, {"affected_count": len(ids)})


@router.get("/announcements/home")
async def home_announcements(request: Request, user: UserDep, session: SessionDep):
    rows = list((await session.scalars(
        select(PlatformMessage).where(
            effective_message_filter(user), PlatformMessage.kind == "announcement"
        ).order_by(case((PlatformMessage.priority == "important", 0), else_=1), PlatformMessage.publish_at.desc()).limit(3)
    )).all())
    return response(request, [message_view(item) for item in rows])


@router.get("/notification-settings")
async def get_notification_settings(request: Request, user: UserDep, session: SessionDep, settings: SettingsDep):
    return response(request, await subscription_settings(session, settings, user.id))


@router.patch("/notification-settings")
async def update_notification_settings(payload: NotificationSettingsUpdate, request: Request, user: UserDep, session: SessionDep):
    now = datetime.now(UTC)
    for kind in ("notification", "announcement"):
        item = await session.get(UserWechatSubscription, (user.id, kind))
        if item is None:
            item = UserWechatSubscription(user_id=user.id, template_kind=kind, status="unknown")
            session.add(item)
        item.enabled = payload.wechat_enabled
        item.updated_at = now
    await session.commit()
    return response(request, {"wechat_enabled": payload.wechat_enabled})


@router.post("/notification-settings/wechat-consent")
async def save_wechat_consent(payload: WechatConsentRequest, request: Request, user: UserDep, session: SessionDep, settings: SettingsDep):
    if not settings.wechat_subscribe_enabled:
        raise ApiError(503, "WECHAT_SUBSCRIBE_NOT_CONFIGURED", "微信订阅消息尚未配置")
    now = datetime.now(UTC)
    mapping = {"accept": "accepted", "reject": "rejected", "ban": "banned"}
    for kind in ("notification", "announcement"):
        value = getattr(payload, kind)
        if value is None:
            continue
        item = await session.get(UserWechatSubscription, (user.id, kind))
        if item is None:
            item = UserWechatSubscription(user_id=user.id, template_kind=kind)
            session.add(item)
        item.status = mapping[value]
        item.enabled = True
        item.consented_at = now if value == "accept" else item.consented_at
        item.updated_at = now
    await session.commit()
    return response(request, await subscription_settings(session, settings, user.id))
