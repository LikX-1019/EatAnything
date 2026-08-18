import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityHistory, Store


async def add_history(session: AsyncSession, *, user_id: int, store_id: int, action: str) -> ActivityHistory:
    history = ActivityHistory(event_key=f"api-{uuid.uuid4().hex}", user_id=user_id, store_id=store_id, action=action)
    session.add(history)
    await session.flush()
    return history


async def count_history(session: AsyncSession, user_id: int, action: str | None = None) -> int:
    from sqlalchemy import func

    query = select(func.count(ActivityHistory.id)).where(ActivityHistory.user_id == user_id)
    if action:
        query = query.where(ActivityHistory.action == action)
    return int((await session.scalar(query)) or 0)


async def list_history(session: AsyncSession, user_id: int, *, action: str | None, page: int, page_size: int) -> list[ActivityHistory]:
    query = select(ActivityHistory).join(Store, Store.id == ActivityHistory.store_id).where(ActivityHistory.user_id == user_id)
    if action:
        query = query.where(ActivityHistory.action == action)
    query = query.order_by(ActivityHistory.occurred_at.desc(), ActivityHistory.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return list((await session.scalars(query)).all())
