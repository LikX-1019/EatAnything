from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckIn, UserFavorite


@dataclass(frozen=True)
class UserStoreFlags:
    is_favorite: bool = False
    is_eaten: bool = False


async def states_for_stores(session: AsyncSession, user_id: int, store_ids: list[int]) -> dict[int, UserStoreFlags]:
    if not store_ids:
        return {}
    favorite_ids = set(
        (await session.scalars(select(UserFavorite.store_id).where(UserFavorite.user_id == user_id, UserFavorite.store_id.in_(store_ids)))).all()
    )
    eaten_ids = set(
        (await session.scalars(select(CheckIn.store_id).where(CheckIn.user_id == user_id, CheckIn.store_id.in_(store_ids), CheckIn.status == "published").distinct())).all()
    )
    return {
        store_id: UserStoreFlags(store_id in favorite_ids, store_id in eaten_ids)
        for store_id in store_ids
        if store_id in favorite_ids or store_id in eaten_ids
    }


async def get_favorite(session: AsyncSession, user_id: int, store_id: int) -> UserFavorite | None:
    return await session.get(UserFavorite, (user_id, store_id))


async def set_favorite(session: AsyncSession, user_id: int, store_id: int, enabled: bool) -> UserFavorite | None:
    favorite = await get_favorite(session, user_id, store_id)
    if enabled:
        if favorite is None:
            favorite = UserFavorite(user_id=user_id, store_id=store_id)
            session.add(favorite)
            await session.flush()
        return favorite
    if favorite is not None:
        await session.delete(favorite)
        await session.flush()
    return None


async def has_check_in(session: AsyncSession, user_id: int, store_id: int) -> bool:
    return bool(await session.scalar(select(CheckIn.id).where(CheckIn.user_id == user_id, CheckIn.store_id == store_id, CheckIn.status == "published").limit(1)))


async def latest_check_in(session: AsyncSession, user_id: int, store_id: int) -> CheckIn | None:
    return await session.scalar(
        select(CheckIn)
        .where(CheckIn.user_id == user_id, CheckIn.store_id == store_id, CheckIn.status == "published")
        .order_by(CheckIn.checked_at.desc(), CheckIn.id.desc())
        .limit(1)
    )


async def count_user_favorites(session: AsyncSession, user_id: int) -> int:
    return int((await session.scalar(select(func.count()).select_from(UserFavorite).where(UserFavorite.user_id == user_id))) or 0)


async def count_user_check_ins(session: AsyncSession, user_id: int) -> int:
    return int((await session.scalar(select(func.count()).select_from(CheckIn).where(CheckIn.user_id == user_id, CheckIn.status == "published"))) or 0)
