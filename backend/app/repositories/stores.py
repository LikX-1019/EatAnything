from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Review, Store


async def count_stores(
    session: AsyncSession,
    *,
    active_only: bool,
    keyword: str | None = None,
    status: str | None = None,
    school_id: int | None = None,
) -> int:
    query = select(func.count(Store.id))
    if active_only:
        query = query.where(Store.status == "active")
    elif status:
        query = query.where(Store.status == status)
    if school_id is not None:
        query = query.where(Store.school_id == school_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(Store.name.ilike(pattern), Store.address.ilike(pattern), Store.slug.ilike(pattern)))
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
) -> list[Store]:
    query = select(Store)
    if active_only:
        query = query.where(Store.status == "active")
    elif status:
        query = query.where(Store.status == status)
    if school_id is not None:
        query = query.where(Store.school_id == school_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(Store.name.ilike(pattern), Store.address.ilike(pattern), Store.slug.ilike(pattern)))
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


async def stats_for_stores(session: AsyncSession, store_ids: Iterable[int]) -> dict[int, tuple[float | None, int]]:
    ids = list(store_ids)
    if not ids:
        return {}
    query = (
        select(Review.store_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.store_id.in_(ids), Review.status == "published")
        .group_by(Review.store_id)
    )
    return {int(store_id): (float(score) if score is not None else None, int(count)) for store_id, score, count in (await session.execute(query)).all()}


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
