from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import MediaObject, SchoolArea, Store, StoreCategory, StoreImage
from app.models.entities import store_category_links
from app.repositories import stores as store_repo
from app.repositories.states import states_for_stores


def category_names(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[·/|,，]+", value) if item.strip()]


async def ensure_categories(session: AsyncSession, value: str) -> list[StoreCategory]:
    result: list[StoreCategory] = []
    for name in category_names(value):
        category = await session.scalar(select(StoreCategory).where(StoreCategory.name == name))
        if category is None:
            category = StoreCategory(name=name)
            session.add(category)
            await session.flush()
        result.append(category)
    return result


async def replace_categories(session: AsyncSession, store_id: int, categories: list[StoreCategory]) -> None:
    await session.execute(delete(store_category_links).where(store_category_links.c.store_id == store_id))
    if categories:
        await session.execute(
            insert(store_category_links),
            [{"store_id": store_id, "category_id": category.id} for category in categories],
        )


def primary_image_url(store: Store, storage: MinioStorage) -> str | None:
    image = next((item for item in store.images if item.is_primary), None)
    if image is None and store.images:
        image = sorted(store.images, key=lambda item: item.sort_order)[0]
    return storage.public_object_url(image.media.object_key) if image else None


def categories_text(store: Store) -> str:
    return " · ".join(sorted((category.name for category in store.categories), key=str))


def store_summary(store: Store, storage: MinioStorage, stats: store_repo.StoreStats, state=None) -> dict:
    return {
        "id": str(store.id),
        "store_code": store.store_code,
        "school_id": str(store.school_id),
        "school_code": store.school.school_code,
        "school_name": store.school.name,
        "area_id": str(store.area_id),
        "area_code": store.area.area_code,
        "name": store.name,
        "category": categories_text(store),
        "address": store.address,
        "area": store.area.name,
        "image_url": primary_image_url(store, storage),
        "score": round(stats.score, 1) if stats.score is not None else None,
        "review_count": stats.review_count,
        "favorite_count": stats.favorite_count,
        "is_favorite": bool(state and state.is_favorite),
        "is_eaten": bool(state and state.is_eaten),
    }


def store_detail(store: Store, storage: MinioStorage, stats: store_repo.StoreStats, state=None) -> dict:
    result = store_summary(store, storage, stats, state)
    result.update(
        {
            "description": store.description,
            "city": store.city,
            "district": store.district,
            "latitude": float(store.latitude) if store.latitude is not None else None,
            "longitude": float(store.longitude) if store.longitude is not None else None,
            "phone": store.phone,
            "business_hours": store.business_hours,
            "created_at": store.created_at.isoformat(),
            "updated_at": store.updated_at.isoformat(),
        }
    )
    return result


async def user_store_page(
    session: AsyncSession,
    storage: MinioStorage,
    user_id: int,
    *,
    keyword: str | None,
    page: int,
    page_size: int,
    mode: str = "all",
    school_id: int | None = None,
) -> tuple[list[dict], int]:
    if mode == "favorites" or mode == "eaten":
        from app.models import CheckIn, UserFavorite
        from sqlalchemy import or_

        relation = UserFavorite if mode == "favorites" else CheckIn
        query = (
            select(Store)
            .join(relation, relation.store_id == Store.id)
            .where(relation.user_id == user_id)
            .distinct()
        )
        if school_id is not None:
            query = query.where(Store.school_id == school_id)
        else:
            return [], 0
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.where(or_(Store.name.ilike(pattern), Store.address.ilike(pattern), Store.store_code.ilike(pattern)))
        total = int((await session.scalar(select(__import__("sqlalchemy").func.count()).select_from(query.subquery()))) or 0)
        stores = list((await session.scalars(query.order_by(Store.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    else:
        if school_id is None:
            return [], 0
        total = await store_repo.count_stores(session, active_only=True, keyword=keyword, school_id=school_id)
        stores = await store_repo.list_stores(
            session,
            active_only=True,
            keyword=keyword,
            status=None,
            page=page,
            page_size=page_size,
            school_id=school_id,
        )
    ids = [store.id for store in stores]
    stats = await store_repo.stats_for_stores(session, ids)
    states = await states_for_stores(session, user_id, ids)
    return [store_summary(store, storage, stats.get(store.id, store_repo.StoreStats()), states.get(store.id)) for store in stores], total


async def get_user_store(session: AsyncSession, storage: MinioStorage, user_id: int, store_id: int) -> dict:
    store = await store_repo.get_store(session, store_id, active_only=True)
    if store is None:
        raise ApiError(404, "STORE_NOT_FOUND", "店铺不存在或已不可用")
    state = await states_for_stores(session, user_id, [store.id])
    stats = await store_repo.stats_for_stores(session, [store.id])
    return store_detail(store, storage, stats.get(store.id, store_repo.StoreStats()), state.get(store.id))


async def random_user_store(
    session: AsyncSession,
    storage: MinioStorage,
    user_id: int,
    exclude_store_id: int | None,
    school_id: int | None,
) -> tuple[dict, str]:
    store_id = (
        await store_repo.random_store_id(session, exclude_store_id, school_id=school_id)
        if school_id is not None
        else None
    )
    if store_id is None:
        raise ApiError(404, "STORE_POOL_EMPTY", "暂无可选店铺")
    store = await store_repo.get_store(session, store_id, active_only=True)
    if store is None:
        raise ApiError(404, "STORE_POOL_EMPTY", "暂无可选店铺")
    state = (await states_for_stores(session, user_id, [store.id])).get(store.id)
    stats = (await store_repo.stats_for_stores(session, [store.id])).get(store.id, store_repo.StoreStats())
    # 抽签结果只有在用户点击“就吃这家！”后才写入历史，避免普通浏览污染记录。
    return store_detail(store, storage, stats, state), ""


async def attach_image(session: AsyncSession, store: Store, image_url: str | None, storage: MinioStorage) -> None:
    if not image_url:
        return
    parsed = urlparse(image_url)
    public = urlparse(storage.public_url)
    prefix = f"{public.path.rstrip('/')}/{storage.bucket}/"
    if (
        parsed.scheme.lower() != public.scheme.lower()
        or parsed.netloc.lower() != public.netloc.lower()
        or not parsed.path.startswith(prefix)
    ):
        raise ApiError(400, "MEDIA_NOT_FOUND", "图片地址不是已上传的媒体对象")
    object_key = unquote(parsed.path[len(prefix):])
    media = await session.scalar(select(MediaObject).where(MediaObject.bucket == storage.bucket, MediaObject.object_key == object_key))
    if media is None:
        raise ApiError(400, "MEDIA_NOT_FOUND", "图片对象不存在，请先上传图片")
    existing_images = list((await session.scalars(select(StoreImage).where(StoreImage.store_id == store.id))).all())
    for image in existing_images:
        image.is_primary = False
    linked = next((image for image in existing_images if image.media_id == media.id), None)
    if linked is None:
        session.add(StoreImage(store_id=store.id, media_id=media.id, is_primary=True, sort_order=0))
    else:
        linked.is_primary = True
        linked.sort_order = 0


async def require_school_area(session: AsyncSession, school_id: int, area_id: int) -> SchoolArea:
    area = await session.scalar(
        select(SchoolArea).where(
            SchoolArea.id == area_id,
            SchoolArea.school_id == school_id,
            SchoolArea.status == "active",
        )
    )
    if area is None:
        raise ApiError(422, "INVALID_SCHOOL_AREA", "区域不存在或不属于所选学校", field="areaId")
    return area


async def admin_store_view(session: AsyncSession, storage: MinioStorage, store: Store) -> dict:
    stats = (await store_repo.stats_for_stores(session, [store.id])).get(store.id, store_repo.StoreStats())
    return {
        **store_summary(store, storage, stats),
        "status": store.status,
        "version": store.version,
        "created_at": store.created_at.isoformat(),
        "updated_at": store.updated_at.isoformat(),
    }


async def create_admin_store(session: AsyncSession, storage: MinioStorage, payload) -> dict:
    await require_school_area(session, payload.school_id, payload.area_id)
    store = Store(
        store_code=payload.store_code,
        school_id=payload.school_id,
        area_id=payload.area_id,
        name=payload.name.strip(),
        address=payload.address.strip(),
        status=payload.status,
    )
    categories = await ensure_categories(session, payload.category)
    session.add(store)
    await session.flush()
    await replace_categories(session, store.id, categories)
    await attach_image(session, store, payload.image_url, storage)
    await session.commit()
    store = await store_repo.get_store(session, store.id, active_only=False)
    if store is None:
        raise ApiError(500, "INTERNAL_ERROR", "店铺保存后无法读取")
    return await admin_store_view(session, storage, store)


async def update_admin_store(session: AsyncSession, storage: MinioStorage, store: Store, payload) -> dict:
    if store.version != payload.version:
        raise ApiError(409, "RESOURCE_VERSION_CONFLICT", "数据已被其他管理员修改，请刷新后重试")
    if payload.name is not None:
        store.name = payload.name.strip()
    target_school_id = payload.school_id if "school_id" in payload.model_fields_set else store.school_id
    target_area_id = payload.area_id if "area_id" in payload.model_fields_set else store.area_id
    if {"school_id", "area_id"} & payload.model_fields_set:
        await require_school_area(session, target_school_id, target_area_id)
        store.school_id = target_school_id
        store.area_id = target_area_id
    if payload.address is not None:
        store.address = payload.address.strip()
    if payload.category is not None:
        categories = await ensure_categories(session, payload.category)
        await replace_categories(session, store.id, categories)
    if payload.status is not None:
        store.status = payload.status
    if payload.image_url is not None:
        await attach_image(session, store, payload.image_url, storage)
    store.version += 1
    await session.commit()
    store = await store_repo.get_store(session, store.id, active_only=False)
    if store is None:
        raise ApiError(500, "INTERNAL_ERROR", "店铺保存后无法读取")
    return await admin_store_view(session, storage, store)
