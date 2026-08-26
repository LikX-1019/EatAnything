from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityHistory, AppUser, Review
from app.repositories.states import count_user_check_ins, count_user_favorites


async def get_user_by_id(session: AsyncSession, user_id: int) -> AppUser | None:
    return await session.get(AppUser, user_id)


async def get_user_by_external_id(session: AsyncSession, external_id: str) -> AppUser | None:
    return await session.scalar(select(AppUser).where(AppUser.external_id == external_id))


async def get_or_create_user(
    session: AsyncSession,
    *,
    external_id: str,
    nickname: str = "微信用户",
    avatar_media_id: int | None = None,
) -> AppUser:
    user = await get_user_by_external_id(session, external_id)
    if user:
        if user.status != "active":
            from app.core.errors import ApiError

            raise ApiError(403, "USER_DISABLED", "当前用户已被禁用")
        return user
    user = AppUser(external_id=external_id, nickname=nickname, avatar_media_id=avatar_media_id)
    session.add(user)
    await session.flush()
    return user


async def user_stats(session: AsyncSession, user_id: int) -> dict[str, int]:
    favorite_count = await count_user_favorites(session, user_id)
    checkin_count = await count_user_check_ins(session, user_id)
    review_count = await session.scalar(select(func.count()).select_from(Review).where(Review.user_id == user_id))
    history_count = await session.scalar(
        select(func.count()).select_from(ActivityHistory).where(
            ActivityHistory.user_id == user_id,
            ActivityHistory.action == "confirmed_pick",
        )
    )
    return {
        "favorite_count": favorite_count,
        "eaten_count": checkin_count,
        "checkin_count": checkin_count,
        "review_count": int(review_count or 0),
        "history_count": int(history_count or 0),
    }
