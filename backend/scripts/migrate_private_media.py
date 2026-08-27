"""将历史用户媒体从公开 bucket 迁移到私有 bucket。

默认只执行 dry-run；设置 ``--apply`` 后才复制对象并更新数据库记录。
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionFactory, engine
from app.integrations.minio import MinioStorage
from app.models import MediaObject


async def migrate(apply: bool) -> int:
    settings = get_settings()
    storage = MinioStorage(settings)
    async with SessionFactory() as session:
        result = await session.scalars(
            select(MediaObject).where(
                MediaObject.purpose.in_(["checkin", "avatar"]),
                MediaObject.bucket != storage.private_bucket,
            )
        )
        items = list(result.all())
        print(f"发现 {len(items)} 条需要迁移的私有媒体记录")
        if not apply:
            await engine.dispose()
            return 0
        for media in items:
            await storage.copy_object(media.object_key, source_bucket=media.bucket, target_bucket=storage.private_bucket)
            media.bucket = storage.private_bucket
        await session.commit()
    await engine.dispose()
    print("私有媒体迁移完成")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移历史用户媒体到私有 MinIO bucket")
    parser.add_argument("--apply", action="store_true", help="实际复制对象并更新数据库；默认只检查")
    args = parser.parse_args()
    return asyncio.run(migrate(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
