from __future__ import annotations

from io import BytesIO
from urllib.parse import quote

import anyio
from minio import Minio

from app.core.config import Settings


class MinioStorage:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.minio_bucket
        self.public_url = settings.minio_public_url.rstrip("/")
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    async def bucket_exists(self) -> bool:
        return await anyio.to_thread.run_sync(self.client.bucket_exists, self.bucket)

    async def put_bytes(self, object_key: str, content: bytes, content_type: str) -> None:
        def upload() -> None:
            self.client.put_object(
                self.bucket,
                object_key,
                BytesIO(content),
                length=len(content),
                content_type=content_type,
            )

        await anyio.to_thread.run_sync(upload)

    async def remove(self, object_key: str) -> None:
        await anyio.to_thread.run_sync(self.client.remove_object, self.bucket, object_key)

    def public_object_url(self, object_key: str) -> str:
        encoded_key = "/".join(quote(part, safe="") for part in object_key.split("/"))
        return f"{self.public_url}/{quote(self.bucket, safe='')}/{encoded_key}"
