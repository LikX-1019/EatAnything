"""只读校验武汉工商学院示例数据。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionFactory, engine  # noqa: E402


EXPECTED = {
    "schools": 1,
    "areas": 2,
    "stores": 10,
    "users": 2,
    "admins": 1,
    "reviews": 10,
    "favorites": 10,
    "images": 10,
    "catalog_rows": 10,
    "catalog_review_count": 10,
    "catalog_favorite_count": 10,
}


QUERY = text(
    """
    SELECT
        (SELECT COUNT(*) FROM schools WHERE school_code = 'wtbu') AS schools,
        (SELECT COUNT(*) FROM school_areas sa JOIN schools s ON s.id = sa.school_id
            WHERE s.school_code = 'wtbu') AS areas,
        (SELECT COUNT(*) FROM stores st JOIN schools s ON s.id = st.school_id
            WHERE s.school_code = 'wtbu') AS stores,
        (SELECT COUNT(*) FROM app_users WHERE external_id IN ('wtbu_test_01', 'wtbu_test_02')) AS users,
        (SELECT COUNT(*) FROM admin_users WHERE username = 'wtbu_admin') AS admins,
        (SELECT COUNT(*) FROM reviews r JOIN app_users u ON u.id = r.user_id
            WHERE u.external_id IN ('wtbu_test_01', 'wtbu_test_02')) AS reviews,
        (SELECT COUNT(*) FROM user_favorites f JOIN app_users u ON u.id = f.user_id
            WHERE u.external_id IN ('wtbu_test_01', 'wtbu_test_02')) AS favorites,
        (SELECT COUNT(*) FROM store_images si JOIN stores st ON st.id = si.store_id
            JOIN schools s ON s.id = st.school_id WHERE s.school_code = 'wtbu') AS images,
        (SELECT COUNT(*) FROM store_catalog WHERE school_code = 'wtbu') AS catalog_rows,
        (SELECT COALESCE(SUM(review_count), 0) FROM store_catalog
            WHERE school_code = 'wtbu') AS catalog_review_count,
        (SELECT COALESCE(SUM(favorite_count), 0) FROM store_catalog
            WHERE school_code = 'wtbu') AS catalog_favorite_count,
        (SELECT COUNT(*) FROM stores st JOIN school_areas sa ON sa.id = st.area_id
            WHERE st.school_id <> sa.school_id) AS invalid_school_area_links
    """
)


async def main() -> None:
    async with SessionFactory() as session:
        row = (await session.execute(QUERY)).mappings().one()
    await engine.dispose()
    actual = {key: int(value) for key, value in row.items()}
    failures = {
        key: {"expected": expected, "actual": actual.get(key)}
        for key, expected in {**EXPECTED, "invalid_school_area_links": 0}.items()
        if actual.get(key) != expected
    }
    print(json.dumps({"ok": not failures, "counts": actual, "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
