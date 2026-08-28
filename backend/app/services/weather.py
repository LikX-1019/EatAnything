"""学校天气缓存同步服务。"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.weather import WeatherProvider
from app.models import School, SchoolWeatherDaily


def local_today(timezone: str, now: datetime | None = None) -> date:
    current = now or datetime.now(UTC)
    return current.astimezone(ZoneInfo(timezone)).date()


async def invalidate_school_weather(session: AsyncSession, school_id: int, timezone: str) -> None:
    await session.execute(
        delete(SchoolWeatherDaily).where(
            SchoolWeatherDaily.school_id == school_id,
            SchoolWeatherDaily.forecast_date >= local_today(timezone),
        )
    )


async def school_needs_weather(
    session: AsyncSession,
    school_id: int,
    timezone: str,
    *,
    now: datetime | None = None,
    refreshed_since: datetime | None = None,
) -> bool:
    today = local_today(timezone, now)
    query = select(SchoolWeatherDaily.forecast_date).where(
        SchoolWeatherDaily.school_id == school_id,
        SchoolWeatherDaily.forecast_date.in_((today, today + timedelta(days=1))),
    )
    if refreshed_since is not None:
        query = query.where(SchoolWeatherDaily.fetched_at >= refreshed_since)
    dates = set((await session.scalars(query)).all())
    return dates != {today, today + timedelta(days=1)}


async def refresh_school_weather(
    session: AsyncSession,
    school: School,
    provider: WeatherProvider,
    timezone: str,
    *,
    now: datetime | None = None,
) -> int:
    if school.latitude is None or school.longitude is None:
        return 0
    fetched_at = now or datetime.now(UTC)
    today = local_today(timezone, fetched_at)
    forecasts = await provider.fetch_daily(Decimal(school.latitude), Decimal(school.longitude))
    valid = [item for item in forecasts if today <= item.forecast_date <= today + timedelta(days=1)]
    if not valid:
        raise ValueError("天气 Provider 未返回当天或次日预报")
    for forecast in valid:
        statement = insert(SchoolWeatherDaily).values(
            school_id=school.id,
            forecast_date=forecast.forecast_date,
            temperature_min=forecast.temperature_min,
            temperature_max=forecast.temperature_max,
            weather_code=forecast.weather_code,
            weather_text=forecast.weather_text,
            icon=forecast.icon,
            provider=forecast.provider,
            fetched_at=fetched_at,
            updated_at=fetched_at,
        ).on_conflict_do_update(
            constraint="uq_school_weather_daily_school_date",
            set_={
                "temperature_min": forecast.temperature_min,
                "temperature_max": forecast.temperature_max,
                "weather_code": forecast.weather_code,
                "weather_text": forecast.weather_text,
                "icon": forecast.icon,
                "provider": forecast.provider,
                "fetched_at": fetched_at,
                "updated_at": fetched_at,
            },
        )
        await session.execute(statement)
    await session.commit()
    return len(valid)
