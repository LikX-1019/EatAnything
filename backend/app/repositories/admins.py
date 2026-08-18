from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminUser


async def get_admin_by_username(session: AsyncSession, username: str) -> AdminUser | None:
    return await session.scalar(select(AdminUser).where(AdminUser.username == username))
