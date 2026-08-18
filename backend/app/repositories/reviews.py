from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Review


async def count_store_reviews(session: AsyncSession, store_id: int) -> int:
    return int((await session.scalar(select(func.count(Review.id)).where(Review.store_id == store_id, Review.status == "published"))) or 0)


async def list_store_reviews(session: AsyncSession, store_id: int, *, page: int, page_size: int) -> list[Review]:
    query = select(Review).where(Review.store_id == store_id, Review.status == "published").order_by(Review.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    return list((await session.scalars(query)).all())


async def list_user_reviews(session: AsyncSession, user_id: int, *, page: int, page_size: int) -> list[Review]:
    query = select(Review).where(Review.user_id == user_id).order_by(Review.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    return list((await session.scalars(query)).all())


async def count_user_reviews(session: AsyncSession, user_id: int) -> int:
    return int((await session.scalar(select(func.count(Review.id)).where(Review.user_id == user_id))) or 0)


async def get_user_review(session: AsyncSession, user_id: int, store_id: int) -> Review | None:
    return await session.scalar(select(Review).where(Review.user_id == user_id, Review.store_id == store_id))
