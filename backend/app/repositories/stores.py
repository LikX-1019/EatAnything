from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Review, Store, UserFavorite


@dataclass(frozen=True, slots=True)
class StoreStats:
    score: float | None = None
    review_count: int = 0
    favorite_count: int = 0


async def count_stores(
    session: AsyncSession,
    *,
    active_only: bool,
    keyword: str | None = None,
    status: str | None = None,
    school_id: int | None = None,
    school_ids: set[int] | None = None,
) -> int:
    query = select(func.count(Store.id))
    if active_only:
        query = query.where(Store.status == "active")
    elif status:
        query = query.where(Store.status == status)
    if school_id is not None:
        query = query.where(Store.school_id == school_id)
    elif school_ids is not None:
        query = query.where(Store.school_id.in_(school_ids or {-1}))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(Store.name.ilike(pattern), Store.address.ilike(pattern), Store.store_code.ilike(pattern)))
    return int((await session.scalar(query)) or 0)


async def list_stores(
    session: AsyncSession,
    *,
    active_only: bool,
    keyword: str | None,
    status: str | None,
    page: int,
    page_size: int,
    school_id: int | None = None,
    school_ids: set[int] | None = None,
) -> list[Store]:
    query = select(Store)
    if active_only:
        query = query.where(Store.status == "active")
    elif status:
        query = query.where(Store.status == status)
    if school_id is not None:
        query = query.where(Store.school_id == school_id)
    elif school_ids is not None:
        query = query.where(Store.school_id.in_(school_ids or {-1}))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(Store.name.ilike(pattern), Store.address.ilike(pattern), Store.store_code.ilike(pattern)))
    query = query.order_by(Store.updated_at.desc(), Store.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return list((await session.scalars(query)).all())


async def get_store(
    session: AsyncSession,
    store_id: int,
    *,
    active_only: bool = True,
    for_update: bool = False,
) -> Store | None:
    query = select(Store).where(Store.id == store_id)
    if active_only:
        query = query.where(Store.status == "active")
    if for_update:
        query = query.with_for_update()
    return await session.scalar(query)


async def stats_for_stores(session: AsyncSession, store_ids: Iterable[int]) -> dict[int, StoreStats]:
    ids = list(store_ids)
    if not ids:
        return {}
    review_stats = (
        select(
            Review.store_id,
            func.avg(Review.rating).label("score"),
            func.count(Review.id).label("review_count"),
        )
        .where(Review.store_id.in_(ids), Review.status == "published")
        .group_by(Review.store_id)
        .subquery()
    )
    favorite_stats = (
        select(UserFavorite.store_id, func.count(UserFavorite.user_id).label("favorite_count"))
        .where(UserFavorite.store_id.in_(ids))
        .group_by(UserFavorite.store_id)
        .subquery()
    )
    query = (
        select(
            Store.id,
            review_stats.c.score,
            review_stats.c.review_count,
            favorite_stats.c.favorite_count,
        )
        .outerjoin(review_stats, review_stats.c.store_id == Store.id)
        .outerjoin(favorite_stats, favorite_stats.c.store_id == Store.id)
        .where(Store.id.in_(ids))
    )
    return {
        int(store_id): StoreStats(
            score=float(score) if score is not None else None,
            review_count=int(review_count or 0),
            favorite_count=int(favorite_count or 0),
        )
        for store_id, score, review_count, favorite_count in (await session.execute(query)).all()
    }


async def random_store_id(
    session: AsyncSession,
    exclude_store_id: int | None = None,
    *,
    school_id: int | None = None,
) -> int | None:
    from sqlalchemy import func as sql_func

    filters = [Store.status == "active"]
    if school_id is not None:
        filters.append(Store.school_id == school_id)
    query = select(Store.id).where(*filters)
    if exclude_store_id is not None:
        candidates = await session.scalar(select(func.count(Store.id)).where(*filters))
        if candidates and candidates > 1:
            query = query.where(Store.id != exclude_store_id)
    return await session.scalar(query.order_by(sql_func.random()).limit(1))
