from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import Review
from app.repositories.reviews import (
    count_store_reviews,
    count_user_reviews,
    get_user_review,
    list_store_reviews,
    list_user_reviews,
)
from app.repositories.states import latest_check_in
from app.repositories.stores import get_store
from app.services.stores import categories_text, primary_image_url
from app.services.moderation import ensure_user_can_comment
from app.services.messages import create_system_message


def reviewer_view(review: Review, storage: MinioStorage) -> dict:
    # 评价列表不能泄漏用户私有头像对象地址，前端使用首字母占位。
    avatar_url = None
    return {
        "id": str(review.id),
        "store_id": str(review.store_id),
        "check_in_id": str(review.check_in_id) if review.check_in_id is not None else None,
        "rating": review.rating,
        "content": review.content,
        "reviewer": {"display_name": review.user.nickname, "avatar_url": avatar_url},
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def snapshot(store, storage: MinioStorage) -> dict:
    return {
        "id": str(store.id),
        "store_code": store.store_code,
        "name": store.name,
        "category": categories_text(store),
        "address": store.address,
        "area": store.area.name,
        "image_url": primary_image_url(store, storage),
        "is_available": store.status == "active",
    }


def my_review_view(review: Review, storage: MinioStorage) -> dict:
    return {
        "id": str(review.id),
        "check_in_id": str(review.check_in_id) if review.check_in_id is not None else None,
        "store": snapshot(review.store, storage),
        "rating": review.rating,
        "content": review.content,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


async def upsert_review(session: AsyncSession, storage: MinioStorage, user_id: int, store_id: int, rating: int, content: str) -> dict:
    await ensure_user_can_comment(session, user_id)
    store = await get_store(session, store_id, active_only=False)
    if store is None or store.status == "closed":
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已关闭")
    existing = await get_user_review(session, user_id, store_id)
    check_in = await latest_check_in(session, user_id, store_id)
    if not existing and check_in is None:
        raise ApiError(403, "REVIEW_REQUIRES_CHECK_IN", "发表评价前必须先完成带图片打卡")
    if existing is not None and existing.check_in_id is None:
        if check_in is None:
            raise ApiError(403, "REVIEW_REQUIRES_CHECK_IN", "发表评价前必须先完成带图片打卡")
        existing.check_in_id = check_in.id
    created = existing is None
    if existing is None:
        existing = Review(user_id=user_id, store_id=store_id, check_in_id=check_in.id, rating=rating, content=content.strip(), status="published")
        session.add(existing)
    else:
        existing.rating = rating
        existing.content = content.strip()
        # 管理员隐藏的评价不能通过用户编辑自行恢复。
        if existing.status != "hidden":
            existing.status = "published"
    await create_system_message(
        session,
        user_id=user_id,
        event_type="review.created" if created else "review.updated",
        title="评价发布成功" if created else "评价更新成功",
        body=f"你对“{store.name}”的评价已{'发布' if created else '更新'}。",
        action_type="reviews",
    )
    await session.commit()
    await session.refresh(existing)
    return my_review_view(existing, storage)


async def store_reviews_page(session: AsyncSession, storage: MinioStorage, store_id: int, page: int, page_size: int) -> tuple[list[dict], int]:
    store = await get_store(session, store_id, active_only=True)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    items = await list_store_reviews(session, store_id, page=page, page_size=page_size)
    total = await count_store_reviews(session, store_id)
    return [reviewer_view(item, storage) for item in items], total


async def user_reviews_page(session: AsyncSession, storage: MinioStorage, user_id: int, page: int, page_size: int) -> tuple[list[dict], int]:
    items = await list_user_reviews(session, user_id, page=page, page_size=page_size)
    total = await count_user_reviews(session, user_id)
    return [my_review_view(item, storage) for item in items], total
