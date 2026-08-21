from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.integrations.minio import MinioStorage


async def main() -> None:
    settings = get_settings()
    connection = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        timeout=8,
    )
    try:
        database_name = await connection.fetchval("SELECT current_database()")
        store_count = await connection.fetchval("SELECT count(*) FROM stores")
    finally:
        await connection.close()

    storage = MinioStorage(settings)
    if not await storage.bucket_exists():
        raise RuntimeError(f"MinIO bucket does not exist: {storage.bucket}")

    print(
        json.dumps(
            {
                "postgres": "ok",
                "database": database_name,
                "stores": store_count,
                "minio": "ok",
                "bucket": storage.bucket,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
