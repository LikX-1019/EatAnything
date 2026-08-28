from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import quote

import nh3
from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.models import (
    AppUser,
    MediaObject,
    MessageMediaLink,
    MessageReadState,
    PlatformMessage,
    UserWechatSubscription,
    WechatDeliveryJob,
)


ACTION_TYPES = {"reviews", "checkins", "settings", "favorites", "history", "stores", "store_detail"}
ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "s", "h2", "h3", "ul", "ol", "li", "blockquote", "img"}
PLAIN_TEXT_RE = re.compile(r"<[^>]+>")


def sanitize_message_html(value: str, settings: Settings) -> str:
    prefix = settings.minio_public_url.rstrip("/") + "/"

    def filter_attribute(tag: str, attribute: str, attribute_value: str) -> str | None:
        if tag == "img" and attribute == "src":
            return attribute_value if attribute_value.startswith(prefix) else None
        return attribute_value

    cleaned = nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes={"img": {"src", "alt", "title"}},
        attribute_filter=filter_attribute,
        set_tag_attribute_values={"img": {"style": "max-width:100%;height:auto;"}},
        clean_content_tags={"script", "style", "iframe", "object"},
        url_schemes={"http", "https"},
        url_relative="deny",
    ).strip()
    image_count = len(re.findall(r"<img\b", cleaned, flags=re.IGNORECASE))
    image_source_count = len(re.findall(r"<img\b[^>]*\bsrc=", cleaned, flags=re.IGNORECASE))
    if image_count != image_source_count:
        raise ApiError(422, "MESSAGE_IMAGE_INVALID", "正文图片必须通过平台上传", field="bodyHtml")
    if not PLAIN_TEXT_RE.sub("", cleaned).strip() and "<img" not in cleaned:
        raise ApiError(422, "MESSAGE_CONTENT_EMPTY", "消息正文不能为空", field="bodyHtml")
    return cleaned


def validate_action(action_type: str | None, action_target_id: int | None) -> None:
    if action_type is None:
        if action_target_id is not None:
            raise ApiError(422, "INVALID_MESSAGE_ACTION", "未选择跳转类型时不能指定目标", field="actionTargetId")
        return
    if action_type not in ACTION_TYPES:
        raise ApiError(422, "INVALID_MESSAGE_ACTION", "不支持的站内跳转", field="actionType")
    if action_type == "store_detail" and action_target_id is None:
        raise ApiError(422, "INVALID_MESSAGE_ACTION", "店铺详情跳转必须指定店铺", field="actionTargetId")
    if action_type != "store_detail" and action_target_id is not None:
        raise ApiError(422, "INVALID_MESSAGE_ACTION", "当前跳转类型不能指定目标 ID", field="actionTargetId")


def effective_message_filter(user: AppUser, now: datetime | None = None):
    current = now or datetime.now(UTC)
    targets = [PlatformMessage.target_type == "all", and_(PlatformMessage.target_type == "user", PlatformMessage.user_id == user.id)]
    if user.school_id is not None:
        targets.append(and_(PlatformMessage.target_type == "school", PlatformMessage.school_id == user.school_id))
    return and_(
        PlatformMessage.status == "published",
        PlatformMessage.publish_at.is_not(None),
        PlatformMessage.publish_at <= current,
        or_(PlatformMessage.expire_at.is_(None), PlatformMessage.expire_at > current),
        or_(*targets),
    )


def message_state(item: PlatformMessage, now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    if item.status == "revoked":
        return "revoked"
    if item.status == "draft":
        return "draft"
    if item.publish_at and item.publish_at > current:
        return "scheduled"
    if item.expire_at and item.expire_at <= current:
        return "expired"
    return "active"


def message_view(item: PlatformMessage, *, is_read: bool = False, include_admin: bool = False, delivery: dict | None = None) -> dict:
    data = {
        "id": str(item.id), "kind": item.kind, "source": item.source, "event_type": item.event_type,
        "title": item.title, "body_html": item.body_html, "priority": item.priority,
        "action_type": item.action_type,
        "action_target_id": str(item.action_target_id) if item.action_target_id is not None else None,
        "publish_at": item.publish_at, "expire_at": item.expire_at, "is_read": is_read,
    }
    if include_admin:
        data.update({
            "target_type": item.target_type,
            "school_id": str(item.school_id) if item.school_id else None,
            "user_id": str(item.user_id) if item.user_id else None,
            "status": item.status, "display_status": message_state(item), "wechat_push": item.wechat_push,
            "created_at": item.created_at, "updated_at": item.updated_at, "delivery": delivery or {},
        })
    return data


async def list_user_messages(session: AsyncSession, user: AppUser, *, kind: str | None, unread_only: bool, page: int, page_size: int) -> tuple[list[dict], int]:
    filters = [effective_message_filter(user)]
    if kind:
        filters.append(PlatformMessage.kind == kind)
    read_join = and_(MessageReadState.message_id == PlatformMessage.id, MessageReadState.user_id == user.id)
    if unread_only:
        filters.append(MessageReadState.message_id.is_(None))
    base = select(PlatformMessage).outerjoin(MessageReadState, read_join).where(*filters)
    total = int((await session.scalar(select(func.count()).select_from(base.subquery()))) or 0)
    rows = (await session.execute(
        select(PlatformMessage, MessageReadState.read_at)
        .outerjoin(MessageReadState, read_join).where(*filters)
        .order_by(case((PlatformMessage.priority == "important", 0), else_=1), PlatformMessage.publish_at.desc(), PlatformMessage.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    return [message_view(item, is_read=read_at is not None) for item, read_at in rows], total


async def unread_count(session: AsyncSession, user: AppUser) -> int:
    return int((await session.scalar(
        select(func.count(PlatformMessage.id)).outerjoin(
            MessageReadState,
            and_(MessageReadState.message_id == PlatformMessage.id, MessageReadState.user_id == user.id),
        ).where(effective_message_filter(user), MessageReadState.message_id.is_(None))
    )) or 0)


async def get_user_message(session: AsyncSession, user: AppUser, message_id: int) -> tuple[PlatformMessage, bool]:
    row = (await session.execute(
        select(PlatformMessage, MessageReadState.read_at).outerjoin(
            MessageReadState,
            and_(MessageReadState.message_id == PlatformMessage.id, MessageReadState.user_id == user.id),
        ).where(PlatformMessage.id == message_id, effective_message_filter(user))
    )).one_or_none()
    if row is None:
        raise ApiError(404, "MESSAGE_NOT_FOUND", "消息不存在或已失效")
    return row[0], row[1] is not None


async def mark_read(session: AsyncSession, user_id: int, message_ids: list[int]) -> None:
    if not message_ids:
        return
    await session.execute(insert(MessageReadState).values([
        {"message_id": message_id, "user_id": user_id} for message_id in message_ids
    ]).on_conflict_do_nothing(index_elements=["message_id", "user_id"]))
    await session.commit()


async def replace_message_media(
    session: AsyncSession, message_id: int, media_ids: list[int], *, body_html: str, settings: Settings,
) -> None:
    media: list[MediaObject] = []
    if media_ids:
        media = list((await session.scalars(select(MediaObject).where(
            MediaObject.id.in_(set(media_ids)), MediaObject.purpose == "message_content"
        ))).all())
        if {item.id for item in media} != set(media_ids):
            raise ApiError(422, "MESSAGE_MEDIA_INVALID", "正文包含无效的消息图片", field="mediaIds")
    expected_urls = {
        f"{settings.minio_public_url.rstrip('/')}/{quote(item.bucket, safe='')}/"
        + "/".join(quote(part, safe="") for part in item.object_key.split("/"))
        for item in media
    }
    image_urls = set(re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', body_html, flags=re.IGNORECASE))
    if not image_urls.issubset(expected_urls):
        raise ApiError(422, "MESSAGE_MEDIA_INVALID", "正文图片必须来自本次关联的平台上传", field="mediaIds")
    await session.execute(delete(MessageMediaLink).where(MessageMediaLink.message_id == message_id))
    for media_id in dict.fromkeys(media_ids):
        session.add(MessageMediaLink(message_id=message_id, media_id=media_id))


async def create_system_message(
    session: AsyncSession, *, user_id: int, event_type: str, title: str, body: str,
    action_type: str | None = None, action_target_id: int | None = None, wechat_push: bool = False,
) -> PlatformMessage:
    now = datetime.now(UTC)
    item = PlatformMessage(
        kind="notification", source="system", event_type=event_type, title=title,
        body_html=f"<p>{nh3.escape(body)}</p>", target_type="user", user_id=user_id,
        priority="important" if wechat_push else "normal", status="published",
        action_type=action_type, action_target_id=action_target_id, wechat_push=wechat_push,
        publish_at=now, published_at=now,
    )
    session.add(item)
    return item


async def subscription_settings(session: AsyncSession, settings: Settings, user_id: int) -> dict:
    rows = {item.template_kind: item for item in (await session.scalars(
        select(UserWechatSubscription).where(UserWechatSubscription.user_id == user_id)
    )).all()}
    return {
        "available": settings.wechat_subscribe_enabled,
        "wechat_enabled": settings.wechat_subscribe_enabled and (any(item.enabled for item in rows.values()) if rows else True),
        "templates": {
            kind: {"template_id": values[0] if values else None, "status": rows.get(kind).status if rows.get(kind) else "unknown"}
            for kind in ("notification", "announcement")
            for values in [settings.wechat_template(kind)]
        },
    }


async def delivery_counts(session: AsyncSession, message_id: int) -> dict:
    rows = (await session.execute(
        select(WechatDeliveryJob.status, func.count(WechatDeliveryJob.id)).where(
            WechatDeliveryJob.message_id == message_id
        ).group_by(WechatDeliveryJob.status)
    )).all()
    return {status: int(count) for status, count in rows}
