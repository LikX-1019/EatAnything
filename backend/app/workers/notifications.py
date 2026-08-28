from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionFactory, engine
from app.integrations.wechat import WechatClient, WechatSendError
from app.models import AppUser, PlatformMessage, UserWechatSubscription, WechatDeliveryJob


logger = configure_logging()
settings = get_settings()
wechat = WechatClient(settings)
TEXT_RE = re.compile(r"<[^>]+>")
RETRY_DELAYS = (60, 300, 1800)


async def prepare_dispatches() -> int:
    if not settings.wechat_subscribe_enabled:
        return 0
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        messages = list((await session.scalars(
            select(PlatformMessage).where(
                PlatformMessage.status == "published", PlatformMessage.wechat_push.is_(True),
                PlatformMessage.publish_at <= now, PlatformMessage.dispatch_prepared_at.is_(None),
                or_(PlatformMessage.expire_at.is_(None), PlatformMessage.expire_at > now),
            ).order_by(PlatformMessage.id).with_for_update(skip_locked=True).limit(20)
        )).all())
        count = 0
        for message in messages:
            filters = [
                UserWechatSubscription.template_kind == message.kind,
                UserWechatSubscription.enabled.is_(True),
                UserWechatSubscription.status == "accepted",
                AppUser.external_id.like("wechat:%"),
            ]
            if message.target_type == "all":
                filters.append(AppUser.status == "active")
            elif message.target_type == "school":
                filters.extend((AppUser.status == "active", AppUser.school_id == message.school_id))
            else:
                filters.append(AppUser.id == message.user_id)
            user_ids = list((await session.scalars(
                select(AppUser.id).join(
                    UserWechatSubscription, UserWechatSubscription.user_id == AppUser.id
                ).where(*filters)
            )).all())
            if user_ids:
                statement = insert(WechatDeliveryJob).values([
                    {"message_id": message.id, "user_id": user_id, "template_kind": message.kind}
                    for user_id in user_ids
                ]).on_conflict_do_nothing(constraint="uq_wechat_delivery_message_user")
                await session.execute(statement)
            message.dispatch_prepared_at = now
            count += len(user_ids)
        await session.commit()
        return count


def template_data(message: PlatformMessage) -> tuple[str, dict] | None:
    template = settings.wechat_template(message.kind)
    if not template:
        return None
    template_id, title_key, content_key, time_key = template
    plain = " ".join(TEXT_RE.sub(" ", message.body_html).split())
    published = message.publish_at or message.created_at
    return template_id, {
        title_key: {"value": message.title[:20]},
        content_key: {"value": plain[:20] or message.title[:20]},
        time_key: {"value": published.astimezone(ZoneInfo(settings.app_timezone)).strftime("%Y-%m-%d %H:%M")},
    }


async def process_jobs() -> int:
    if not settings.wechat_subscribe_enabled:
        return 0
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        jobs = list((await session.scalars(
            select(WechatDeliveryJob).where(
                WechatDeliveryJob.status.in_(("pending", "retry")), WechatDeliveryJob.next_attempt_at <= now
            ).order_by(WechatDeliveryJob.id).with_for_update(skip_locked=True).limit(20)
        )).all())
        for job in jobs:
            job.status = "processing"
            job.attempts += 1
            job.updated_at = now
        await session.commit()

    processed = 0
    for job in jobs:
        async with SessionFactory() as session:
            current = await session.get(WechatDeliveryJob, job.id, with_for_update=True)
            if current is None or current.status != "processing":
                continue
            message = await session.get(PlatformMessage, current.message_id)
            user = await session.get(AppUser, current.user_id)
            subscription = await session.get(UserWechatSubscription, (current.user_id, current.template_kind))
            now = datetime.now(UTC)
            if not message or not user or not subscription or message.status != "published" or (message.expire_at and message.expire_at <= now):
                current.status = "skipped"
                current.last_error_code = "MESSAGE_INACTIVE"
                current.last_error_message = "消息已失效或接收人不存在"
                await session.commit()
                continue
            template = template_data(message)
            if not template or not user.external_id.startswith("wechat:"):
                current.status = "skipped"
                current.last_error_code = "WECHAT_NOT_CONFIGURED"
                current.last_error_message = "微信模板未配置或用户不是微信账号"
                await session.commit()
                continue
            template_id, data = template
            try:
                await wechat.send_subscribe_message(
                    openid=user.external_id.removeprefix("wechat:"), template_id=template_id,
                    page=f"pages/messages/detail?id={message.id}", data=data,
                )
                current.status = "sent"
                current.sent_at = now
                current.last_error_code = None
                current.last_error_message = None
                subscription.status = "consumed"
                subscription.last_sent_at = now
                subscription.updated_at = now
                logger.info("wechat_message_sent", message_id=message.id, user_id=user.id, kind=message.kind)
            except WechatSendError as exc:
                current.last_error_code = exc.code[:80]
                current.last_error_message = str(exc)[:500]
                if exc.transient and current.attempts <= len(RETRY_DELAYS):
                    current.status = "retry"
                    current.next_attempt_at = now + timedelta(seconds=RETRY_DELAYS[current.attempts - 1])
                else:
                    current.status = "failed"
                    if not exc.transient:
                        subscription.status = "needs_reauth"
                        subscription.updated_at = now
                logger.warning("wechat_message_failed", message_id=message.id, user_id=user.id, code=exc.code, transient=exc.transient)
            current.updated_at = now
            await session.commit()
            processed += 1
    return processed


async def recover_stale_jobs() -> None:
    cutoff = datetime.now(UTC) - timedelta(minutes=10)
    async with SessionFactory() as session:
        jobs = list((await session.scalars(select(WechatDeliveryJob).where(
            WechatDeliveryJob.status == "processing", WechatDeliveryJob.updated_at < cutoff
        ))).all())
        for job in jobs:
            job.status = "retry"
            job.next_attempt_at = datetime.now(UTC)
        await session.commit()


async def run() -> None:
    await recover_stale_jobs()
    logger.info("notification_worker_started", wechat_enabled=settings.wechat_subscribe_enabled)
    try:
        while True:
            prepared = await prepare_dispatches()
            processed = await process_jobs()
            await asyncio.sleep(1 if prepared or processed else 5)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
