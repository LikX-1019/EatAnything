"""幂等初始化武汉工商学院演示数据。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import sys
from datetime import date
from pathlib import Path

from PIL import Image
from sqlalchemy import delete, select, update


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionFactory, engine  # noqa: E402
from app.integrations.minio import MinioStorage  # noqa: E402
from app.models import (  # noqa: E402
    AdminUser,
    AppUser,
    CheckIn,
    MediaObject,
    Review,
    School,
    SchoolArea,
    Store,
    StoreCategory,
    StoreImage,
    UserFavorite,
)
from app.models.entities import store_category_links  # noqa: E402


SCHOOL_CODE = "wtbu"
ADMIN_USERNAME = "wtbu_admin"
TEST_USERS = (
    ("wtbu_test_01", "南区试吃员", "爱吃、会拍、认真评价"),
    ("wtbu_test_02", "北区探店员", "今天也要好好吃饭"),
)
AREAS = (
    ("south-canteen", "南区食堂", 10, "武汉工商学院南区餐饮区域"),
    ("north-canteen", "北区食堂", 20, "武汉工商学院北区餐饮区域"),
)
STORES = (
    ("wtbu-south-001", "south-canteen", "南区一品香自选餐", "自选餐", "南区食堂一层 01 号", "rice-bowl.jpg", 5, "菜品选择多，荤素搭配方便。"),
    ("wtbu-south-002", "south-canteen", "楚味热干面", "面食", "南区食堂一层 02 号", "lanzhou-noodles.jpg", 4, "芝麻酱香味足，出餐速度快。"),
    ("wtbu-south-003", "south-canteen", "西北兰州牛肉面", "面食", "南区食堂一层 03 号", "lanzhou-noodles.jpg", 5, "汤底清爽，面条筋道。"),
    ("wtbu-south-004", "south-canteen", "金牌黄焖鸡米饭", "盖饭", "南区食堂二层 04 号", "rice-bowl.jpg", 4, "分量足，酱汁很下饭。"),
    ("wtbu-south-005", "south-canteen", "甜啦啦饮品站", "饮品", "南区食堂一层 05 号", "bubble-tea.jpg", 5, "饮品清爽，甜度可以选择。"),
    ("wtbu-north-001", "north-canteen", "北区老坛酸菜鱼", "川湘菜", "北区食堂一层 01 号", "hotpot.jpg", 4, "酸辣开胃，鱼片口感嫩。"),
    ("wtbu-north-002", "north-canteen", "韩式石锅拌饭", "韩餐", "北区食堂一层 02 号", "korean-bbq.jpg", 5, "配菜丰富，锅巴很香。"),
    ("wtbu-north-003", "north-canteen", "山城重庆小面", "面食", "北区食堂一层 03 号", "lanzhou-noodles.jpg", 4, "麻辣鲜香，可以调整辣度。"),
    ("wtbu-north-004", "north-canteen", "北方手作水饺", "饺子", "北区食堂二层 04 号", "sushi.jpg", 5, "现煮水饺，馅料扎实。"),
    ("wtbu-north-005", "north-canteen", "元气轻食工坊", "轻食", "北区食堂二层 05 号", "cheeseburger.jpg", 4, "搭配清爽，适合控制热量。"),
)


def _seed_password() -> str:
    settings = get_settings()
    if settings.seed_admin_password:
        if len(settings.seed_admin_password) < 12:
            raise RuntimeError("SEED_ADMIN_PASSWORD 至少需要 12 个字符")
        return settings.seed_admin_password

    password = secrets.token_urlsafe(24)
    env_path = PROJECT_ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    replacement = f'SEED_ADMIN_PASSWORD="{password}"'
    for index, line in enumerate(lines):
        if line.lstrip().startswith("SEED_ADMIN_PASSWORD="):
            lines[index] = replacement
            break
    else:
        if lines and lines[-1]:
            lines.append("")
        lines.extend(["# 武汉工商学院示例管理员密码（请勿提交）", replacement])
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    return password


async def _upsert_school(session) -> School:
    school = await session.scalar(select(School).where(School.school_code == SCHOOL_CODE))
    if school is None:
        school = School(school_code=SCHOOL_CODE, name="武汉工商学院")
        session.add(school)
    school.name = "武汉工商学院"
    school.city = "武汉市"
    school.district = "洪山区"
    school.address = "湖北省武汉市洪山区黄家湖西路3号"
    school.status = "active"
    await session.flush()
    return school


async def _upsert_areas(session, school: School) -> dict[str, SchoolArea]:
    result: dict[str, SchoolArea] = {}
    for area_code, name, sort_order, description in AREAS:
        area = await session.scalar(
            select(SchoolArea).where(
                SchoolArea.school_id == school.id,
                SchoolArea.area_code == area_code,
            )
        )
        if area is None:
            area = SchoolArea(school_id=school.id, area_code=area_code, name=name)
            session.add(area)
        area.name = name
        area.sort_order = sort_order
        area.description = description
        area.status = "active"
        await session.flush()
        result[area_code] = area
    return result


async def _upsert_category(session, name: str) -> StoreCategory:
    category = await session.scalar(select(StoreCategory).where(StoreCategory.name == name))
    if category is None:
        category = StoreCategory(name=name)
        session.add(category)
        await session.flush()
    return category


async def _upsert_media(session, storage: MinioStorage, store_code: str, filename: str) -> MediaObject:
    image_path = BACKEND_ROOT / "seed_assets" / filename
    content = image_path.read_bytes()
    object_key = f"stores/{SCHOOL_CODE}/{store_code}/cover.jpg"
    await storage.put_bytes(object_key, content, "image/jpeg")
    with Image.open(image_path) as image:
        width, height = image.size
    media = await session.scalar(
        select(MediaObject).where(
            MediaObject.bucket == storage.bucket,
            MediaObject.object_key == object_key,
        )
    )
    if media is None:
        media = MediaObject(
            bucket=storage.bucket,
            object_key=object_key,
            original_filename=filename,
            content_type="image/jpeg",
        )
        session.add(media)
    media.original_filename = filename
    media.content_type = "image/jpeg"
    media.size_bytes = len(content)
    media.width = width
    media.height = height
    media.checksum_sha256 = hashlib.sha256(content).hexdigest()
    media.source_provider = "project_asset"
    media.purpose = "store_cover"
    media.upload_state = "attached"
    await session.flush()
    return media


async def _upsert_stores(session, storage: MinioStorage, school: School, areas: dict[str, SchoolArea]):
    result: list[Store] = []
    media_by_store: dict[int, MediaObject] = {}
    business_hours = {
        "timezone": "Asia/Shanghai",
        "weekly": {
            "mon-fri": ["06:30-21:30"],
            "sat-sun": ["07:00-21:00"],
        },
    }
    for store_code, area_code, name, category_name, address, image_name, _, _ in STORES:
        area = areas[area_code]
        store = await session.scalar(select(Store).where(Store.store_code == store_code))
        if store is None:
            store = Store(
                store_code=store_code,
                school_id=school.id,
                area_id=area.id,
                name=name,
                address=address,
            )
            session.add(store)
        store.school_id = school.id
        store.area_id = area.id
        store.name = name
        store.description = f"武汉工商学院{area.name}{name}示例店铺。"
        store.city = school.city
        store.district = school.district
        store.address = address
        store.business_hours = business_hours
        store.status = "active"
        await session.flush()

        category = await _upsert_category(session, category_name)
        await session.execute(delete(store_category_links).where(store_category_links.c.store_id == store.id))
        await session.execute(
            store_category_links.insert().values(store_id=store.id, category_id=category.id)
        )

        media = await _upsert_media(session, storage, store_code, image_name)
        await session.execute(
            update(StoreImage).where(StoreImage.store_id == store.id).values(is_primary=False)
        )
        image_link = await session.scalar(
            select(StoreImage).where(StoreImage.store_id == store.id, StoreImage.media_id == media.id)
        )
        if image_link is None:
            image_link = StoreImage(store_id=store.id, media_id=media.id)
            session.add(image_link)
        image_link.is_primary = True
        image_link.sort_order = 0
        await session.flush()
        result.append(store)
        media_by_store[store.id] = media
    return result, media_by_store


async def _upsert_users(session, school: School) -> list[AppUser]:
    users: list[AppUser] = []
    for external_id, nickname, slogan in TEST_USERS:
        user = await session.scalar(select(AppUser).where(AppUser.external_id == external_id))
        if user is None:
            user = AppUser(external_id=external_id, nickname=nickname)
            session.add(user)
        user.school_id = school.id
        user.nickname = nickname
        user.slogan = slogan
        user.level = 1
        user.status = "active"
        await session.flush()
        users.append(user)
    return users


async def _upsert_interactions(session, users: list[AppUser], stores: list[Store], media_by_store):
    for index, store in enumerate(stores):
        user = users[index % len(users)]
        favorite = await session.scalar(
            select(UserFavorite).where(
                UserFavorite.user_id == user.id,
                UserFavorite.store_id == store.id,
            )
        )
        if favorite is None:
            session.add(UserFavorite(user_id=user.id, store_id=store.id))

        check_in = await session.scalar(
            select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.store_id == store.id)
        )
        if check_in is None:
            check_in = CheckIn(
                user_id=user.id,
                store_id=store.id,
                photo_media_id=media_by_store[store.id].id,
                note="示例账号到店打卡",
            )
            session.add(check_in)
            await session.flush()

        rating = STORES[index][6]
        content = STORES[index][7]
        review = await session.scalar(
            select(Review).where(Review.user_id == user.id, Review.store_id == store.id)
        )
        if review is None:
            review = Review(user_id=user.id, store_id=store.id, rating=rating, content=content)
            session.add(review)
        review.check_in_id = check_in.id
        review.rating = rating
        review.content = content
        review.visited_at = date.today()
        review.status = "published"


async def _upsert_admin(session, password: str) -> AdminUser:
    admin = await session.scalar(select(AdminUser).where(AdminUser.username == ADMIN_USERNAME))
    if admin is None:
        admin = AdminUser(
            username=ADMIN_USERNAME,
            password_hash=hash_password(password),
            display_name="武汉工商学院管理员",
        )
        session.add(admin)
    else:
        admin.password_hash = hash_password(password)
    admin.display_name = "武汉工商学院管理员"
    admin.role = "store_admin"
    admin.status = "active"
    await session.flush()
    return admin


async def main() -> None:
    password = _seed_password()
    settings = get_settings()
    storage = MinioStorage(settings)
    if not await storage.bucket_exists():
        raise RuntimeError(f"MinIO 存储桶不存在：{storage.bucket}")

    async with SessionFactory() as session:
        try:
            school = await _upsert_school(session)
            areas = await _upsert_areas(session, school)
            stores, media_by_store = await _upsert_stores(session, storage, school, areas)
            users = await _upsert_users(session, school)
            await _upsert_interactions(session, users, stores, media_by_store)
            await _upsert_admin(session, password)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await engine.dispose()

    print(
        json.dumps(
            {
                "学校": "武汉工商学院",
                "区域数": len(AREAS),
                "店铺数": len(STORES),
                "测试账号": [external_id for external_id, _, _ in TEST_USERS],
                "管理员账号": ADMIN_USERNAME,
                "管理员密码位置": "项目根目录 .env 的 SEED_ADMIN_PASSWORD",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
