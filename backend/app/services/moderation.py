from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models import AdminAuditLog, AdminUser, UserRestriction


def restriction_active(blocked: bool, blocked_until: datetime | None) -> bool:
    if not blocked:
        return False
    if blocked_until is None:
        return True
    return blocked_until > datetime.now(UTC)


async def ensure_user_can_comment(session: AsyncSession, user_id: int) -> None:
    restriction = await session.get(UserRestriction, user_id)
    if restriction and restriction_active(restriction.comment_blocked, restriction.comment_blocked_until):
        raise ApiError(403, "COMMENT_BLOCKED", "当前账号已被禁止发表评论")


async def ensure_user_can_upload_image(session: AsyncSession, user_id: int) -> None:
    restriction = await session.get(UserRestriction, user_id)
    if restriction and restriction_active(restriction.image_upload_blocked, restriction.image_upload_blocked_until):
        raise ApiError(403, "IMAGE_UPLOAD_BLOCKED", "当前账号已被禁止上传图片")


def add_audit_log(
    session: AsyncSession,
    request: Request,
    admin: AdminUser,
    *,
    action: str,
    target_type: str,
    target_id: str | int,
    school_id: int | None = None,
    reason: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    client = request.client
    session.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            school_id=school_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            reason=reason,
            before_data=before,
            after_data=after,
            ip_address=client.host if client else None,
            user_agent=request.headers.get("user-agent", "")[:500] or None,
        )
    )
