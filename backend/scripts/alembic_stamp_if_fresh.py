"""数据库迁移入口：验证 baseline 后执行 Alembic stamp/upgrade。

策略：
- 数据库已有 alembic_version 表：直接执行 `alembic upgrade head`。
- 数据库没有 alembic_version 表（全新 baseline 库）：
    1. 校验 001_schema.sql baseline 的关键 schema 特征（见 BASELINE_FINGERPRINT）；
    2. 校验失败：fail closed，返回非 0，不执行任何 stamp/upgrade；
    3. 校验成功：`alembic stamp BASELINE_REVISION`，再继续 `alembic upgrade head`。

baseline 对应的明确 revision 是 0006_admin_governance。全新库初始化
必须 stamp 到这个固定 revision，禁止用不指定 revision 的动态 stamp，
否则未来新增 0007/0008 迁移时会被错误跳过。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
# 001_schema.sql baseline 对应的明确 Alembic revision
BASELINE_REVISION = "0006_admin_governance"

# baseline 关键 schema 特征：全部通过才允许 stamp，否则 fail closed
BASELINE_FINGERPRINT = (
    ("admin_users 表存在", "SELECT to_regclass('public.admin_users') IS NOT NULL"),
    ("school_areas 表存在", "SELECT to_regclass('public.school_areas') IS NOT NULL"),
    ("check_ins 表存在", "SELECT to_regclass('public.check_ins') IS NOT NULL"),
    ("admin_user_schools 表存在", "SELECT to_regclass('public.admin_user_schools') IS NOT NULL"),
    ("user_restrictions 表存在", "SELECT to_regclass('public.user_restrictions') IS NOT NULL"),
    ("admin_audit_logs 表存在", "SELECT to_regclass('public.admin_audit_logs') IS NOT NULL"),
    (
        "stores.store_code 列存在",
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'stores' AND column_name = 'store_code')",
    ),
    (
        "stores.area_id 列存在",
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'stores' AND column_name = 'area_id')",
    ),
    (
        "stores.slug 列不存在",
        "SELECT NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'stores' AND column_name = 'slug')",
    ),
    (
        "stores.area 列不存在",
        "SELECT NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'stores' AND column_name = 'area')",
    ),
    (
        "idx_media_objects_owner_purpose 索引存在",
        "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'media_objects' AND indexname = 'idx_media_objects_owner_purpose')",
    ),
)


async def _version_table_exists() -> bool:
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.db.session import SessionFactory, engine

    async with SessionFactory() as session:
        result = await session.scalar(text("SELECT to_regclass('public.alembic_version')"))
    await engine.dispose()
    return result is not None


async def _fingerprint_failures() -> list[str]:
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.db.session import SessionFactory, engine

    failures: list[str] = []
    async with SessionFactory() as session:
        for description, statement in BASELINE_FINGERPRINT:
            if not bool(await session.scalar(text(statement))):
                failures.append(description)
    await engine.dispose()
    return failures


def _run_alembic(*, stamp: str | None = None, upgrade: str | None = None) -> None:
    sys.path.insert(0, str(BACKEND_ROOT))
    os.chdir(BACKEND_ROOT)
    config = Config(str(ALEMBIC_INI))
    if stamp is not None:
        command.stamp(config, stamp)
    if upgrade is not None:
        command.upgrade(config, upgrade)


def main() -> int:
    if asyncio.run(_version_table_exists()):
        print("检测到 alembic_version 表，直接执行 alembic upgrade head")
        _run_alembic(upgrade="head")
        return 0

    failures = asyncio.run(_fingerprint_failures())
    if failures:
        for item in failures:
            print(f"baseline 校验失败：{item}", file=sys.stderr)
        print(
            "数据库不匹配 001_schema.sql baseline，已 fail closed，"
            "未执行任何 stamp/upgrade。请确认数据库来源后再处理。",
            file=sys.stderr,
        )
        return 2

    print(f"全新 baseline 校验通过，执行 alembic stamp {BASELINE_REVISION}")
    _run_alembic(stamp=BASELINE_REVISION)
    print("继续执行 alembic upgrade head")
    _run_alembic(upgrade="head")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
