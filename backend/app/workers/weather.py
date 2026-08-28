"""每天 06:00 更新学校天气，并为缺失缓存执行补抓。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionFactory, engine
from app.integrations.weather import create_weather_provider
from app.models import School
from app.services.weather import refresh_school_weather, school_needs_weather


logger = configure_logging()
settings = get_settings()
provider = create_weather_provider(settings)
CHECK_INTERVAL_SECONDS = 30 * 60


def refresh_window_start(now: datetime | None = None) -> datetime:
    current = (now or datetime.now(UTC)).astimezone(ZoneInfo(settings.app_timezone))
    target = datetime.combine(current.date(), time(hour=6), tzinfo=current.tzinfo)
    if current < target:
        target -= timedelta(days=1)
    return target.astimezone(UTC)


async def refresh_schools(*, now: datetime | None = None) -> tuple[int, int]:
    refreshed = 0
    failed = 0
    async with SessionFactory() as session:
        schools = list((await session.scalars(
            select(School).where(School.status == "active").order_by(School.id)
        )).all())
        for school in schools:
            if school.latitude is None or school.longitude is None:
                logger.warning("weather_school_coordinates_missing", school_id=school.id)
                continue
            if not await school_needs_weather(
                session,
                school.id,
                settings.app_timezone,
                now=now,
                refreshed_since=refresh_window_start(now),
            ):
                continue
            try:
                count = await refresh_school_weather(session, school, provider, settings.app_timezone)
                refreshed += count
                logger.info(
                    "weather_school_refreshed",
                    school_id=school.id,
                    provider=settings.weather_provider,
                    forecast_count=count,
                )
            except Exception as exc:
                await session.rollback()
                failed += 1
                logger.warning(
                    "weather_school_refresh_failed",
                    school_id=school.id,
                    provider=settings.weather_provider,
                    error_type=type(exc).__name__,
                )
    return refreshed, failed


async def run() -> None:
    logger.info("weather_worker_started", provider=settings.weather_provider, timezone=settings.app_timezone)
    try:
        while True:
            await refresh_schools()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
