from __future__ import annotations

import csv
import io
import re
from typing import Any
from urllib.parse import urlparse

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiError
from app.integrations.minio import MinioStorage
from app.models import Store
from app.services.stores import attach_image, ensure_categories, replace_categories


HEADERS = ["storeCode", "name", "category", "address", "imageUrl", "status"]
VALID_STATUSES = {"active", "hidden", "closed"}


def _cell(value: Any) -> str:
    return "" if value is None else str(value).strip()


async def parse_rows(content: bytes, filename: str, settings: Settings) -> list[dict[str, str]]:
    if len(content) > settings.max_upload_bytes:
        raise ApiError(413, "FILE_TOO_LARGE", "文件不能超过设定大小")
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "CSV 必须使用 UTF-8 编码") from exc
        rows = list(csv.reader(io.StringIO(text)))
    elif suffix == "xlsx":
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
            sheet = workbook.active
            rows = [[cell.value for cell in row] for row in sheet.iter_rows()]
        except Exception as exc:
            raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "XLSX 文件无法解析") from exc
    else:
        raise ApiError(415, "UNSUPPORTED_FILE_TYPE", "仅支持 CSV 或 XLSX 文件")
    if not rows:
        raise ApiError(422, "IMPORT_VALIDATION_FAILED", "导入文件不能为空")
    headers = [_cell(value) for value in rows[0]]
    if headers != HEADERS:
        raise ApiError(422, "IMPORT_VALIDATION_FAILED", "表头必须为 storeCode,name,category,address,imageUrl,status")
    data_rows = [row for row in rows[1:] if any(_cell(value) for value in row)]
    if not data_rows:
        raise ApiError(422, "IMPORT_VALIDATION_FAILED", "导入文件没有数据行")
    if len(data_rows) > 1000:
        raise ApiError(422, "IMPORT_VALIDATION_FAILED", "数据行不能超过 1000 行")
    errors: list[dict] = []
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for row_number, row in enumerate(data_rows, start=2):
        values = [_cell(value) for value in row]
        values += [""] * (len(HEADERS) - len(values))
        item = dict(zip(HEADERS, values[: len(HEADERS)]))
        item["storeCode"] = item["storeCode"].lower()
        if item["storeCode"] in seen:
            errors.append({"row": row_number, "field": "storeCode", "code": "DUPLICATE_STORE_CODE_IN_FILE", "message": "店铺编码在文件中重复"})
        seen.add(item["storeCode"])
        for field, max_length in [("storeCode", 100), ("name", 120), ("category", 50), ("address", 255)]:
            if not item[field]:
                errors.append({"row": row_number, "field": field, "code": "REQUIRED_FIELD", "message": "字段不能为空"})
            elif len(item[field]) > max_length:
                errors.append({"row": row_number, "field": field, "code": "FIELD_TOO_LONG", "message": "字段长度超出限制"})
        if item["storeCode"] and not re.fullmatch(r"[a-z0-9_-]{2,100}", item["storeCode"]):
            errors.append({"row": row_number, "field": "storeCode", "code": "INVALID_STORE_CODE", "message": "店铺编码只能包含小写字母、数字、- 和 _"})
        if item["status"] not in VALID_STATUSES:
            errors.append({"row": row_number, "field": "status", "code": "INVALID_ENUM_VALUE", "message": "状态必须为 active、hidden 或 closed"})
        if item["imageUrl"]:
            parsed_url = urlparse(item["imageUrl"])
            if parsed_url.scheme != "https" and parsed_url.scheme != "http":
                errors.append({"row": row_number, "field": "imageUrl", "code": "INVALID_URL", "message": "图片地址必须是 HTTP(S) URL"})
        parsed.append(item)
    if errors:
        raise ApiError(422, "IMPORT_VALIDATION_FAILED", "导入文件包含错误，未写入任何店铺", details=errors)
    return parsed


async def import_stores(session: AsyncSession, storage: MinioStorage, settings: Settings, content: bytes, filename: str) -> dict:
    rows = await parse_rows(content, filename, settings)
    codes = [row["storeCode"] for row in rows]
    existing = {store.slug: store for store in (await session.scalars(select(Store).where(Store.slug.in_(codes)))).all()}
    results = []
    try:
        for row_index, row in enumerate(rows, start=2):
            store = existing.get(row["storeCode"])
            action = "updated" if store else "created"
            if store is None:
                store = Store(slug=row["storeCode"], name=row["name"], address=row["address"], status=row["status"])
                session.add(store)
                await session.flush()
                existing[store.slug] = store
            else:
                store.name = row["name"]
                store.address = row["address"]
                store.status = row["status"]
                store.version += 1
            categories = await ensure_categories(session, row["category"])
            await replace_categories(session, store.id, categories)
            if row["imageUrl"]:
                await attach_image(session, store, row["imageUrl"], storage)
            elif store.status == "active" and not store.images:
                raise ApiError(422, "IMPORT_VALIDATION_FAILED", "已上架店铺必须提供图片", field="imageUrl")
            results.append({"row": row_index, "store_code": store.slug, "store_id": str(store.id), "action": action})
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return {"total_rows": len(rows), "created_count": sum(item["action"] == "created" for item in results), "updated_count": sum(item["action"] == "updated" for item in results), "items": results}
