from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models import AdminUser, AdminUserSchool


def is_platform_admin(admin: AdminUser) -> bool:
    return admin.role in {"platform_admin", "store_admin"}


async def admin_school_ids(session: AsyncSession, admin: AdminUser) -> set[int] | None:
    if is_platform_admin(admin):
        return None
    return set(
        (await session.scalars(select(AdminUserSchool.school_id).where(AdminUserSchool.admin_user_id == admin.id))).all()
    )


async def scoped_school_id(
    session: AsyncSession,
    admin: AdminUser,
    requested_school_id: int | None,
) -> int | None:
    scope = await admin_school_ids(session, admin)
    if scope is None:
        return requested_school_id
    if requested_school_id is not None and requested_school_id not in scope:
        raise ApiError(403, "FORBIDDEN", "无权访问该学校数据")
    if requested_school_id is not None:
        return requested_school_id
    if len(scope) == 1:
        return next(iter(scope))
    return None


async def ensure_school_allowed(session: AsyncSession, admin: AdminUser, school_id: int) -> None:
    scope = await admin_school_ids(session, admin)
    if scope is not None and school_id not in scope:
        raise ApiError(403, "FORBIDDEN", "无权管理该学校数据")
