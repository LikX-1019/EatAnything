from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppUser, CheckIn, UserFavorite


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


async def authorized_state_for_store(
    session: AsyncSession,
    user_id: int,
    school_id: int,
    store_id: int,
) -> UserStoreFlags | None:
    """用一次 SQL 校验用户学校并读取单个店铺的收藏和打卡状态。"""
    active_user_exists = select(AppUser.id).where(
        AppUser.id == user_id,
        AppUser.status == "active",
        AppUser.school_id == school_id,
    ).exists()
    favorite_exists = select(UserFavorite.user_id).where(
        UserFavorite.user_id == user_id,
        UserFavorite.store_id == store_id,
    ).exists()
    eaten_exists = select(CheckIn.id).where(
        CheckIn.user_id == user_id,
        CheckIn.store_id == store_id,
        CheckIn.status == "published",
    ).exists()
    is_active, is_favorite, is_eaten = (
        await session.execute(select(active_user_exists, favorite_exists, eaten_exists))
    ).one()
    if not is_active:
        return None
    return UserStoreFlags(bool(is_favorite), bool(is_eaten))


async def get_favorite(session: AsyncSession, user_id: int, store_id: int) -> UserFavorite | None:
    return await session.get(UserFavorite, (user_id, store_id))


async def set_favorite(session: AsyncSession, user_id: int, store_id: int, enabled: bool) -> UserFavorite | None:
    if enabled:
        # PUT 必须保持幂等；数据库级冲突忽略可避免并发请求在“先查后写”之间重复插入。
        statement = (
            insert(UserFavorite)
            .values(user_id=user_id, store_id=store_id)
            .on_conflict_do_nothing(index_elements=[UserFavorite.user_id, UserFavorite.store_id])
        )
        await session.execute(statement)
        return await get_favorite(session, user_id, store_id)
    # DELETE 同样直接按主键执行，重复取消收藏不会报错。
    await session.execute(
        delete(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.store_id == store_id,
        )
    )
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
