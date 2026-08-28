"""学校天气 Provider 适配器。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

import httpx

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class DailyWeatherForecast:
    forecast_date: date
    temperature_min: Decimal
    temperature_max: Decimal
    weather_code: str
    weather_text: str
    icon: str
    provider: str


class WeatherProvider(Protocol):
    async def fetch_daily(self, latitude: Decimal, longitude: Decimal) -> list[DailyWeatherForecast]: ...


WMO_WEATHER: dict[int, tuple[str, str]] = {
    0: ("晴", "☀️"),
    1: ("晴间多云", "🌤️"),
    2: ("多云", "⛅"),
    3: ("阴", "☁️"),
    45: ("雾", "🌫️"),
    48: ("雾凇", "🌫️"),
    51: ("小毛毛雨", "🌦️"),
    53: ("毛毛雨", "🌦️"),
    55: ("强毛毛雨", "🌧️"),
    56: ("冻毛毛雨", "🌧️"),
    57: ("强冻毛毛雨", "🌧️"),
    61: ("小雨", "🌦️"),
    63: ("中雨", "🌧️"),
    65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"),
    67: ("强冻雨", "🌧️"),
    71: ("小雪", "🌨️"),
    73: ("中雪", "🌨️"),
    75: ("大雪", "❄️"),
    77: ("米雪", "🌨️"),
    80: ("小阵雨", "🌦️"),
    81: ("中阵雨", "🌧️"),
    82: ("强阵雨", "🌧️"),
    85: ("小阵雪", "🌨️"),
    86: ("大阵雪", "❄️"),
    95: ("雷阵雨", "⛈️"),
    96: ("雷阵雨伴冰雹", "⛈️"),
    99: ("强雷阵雨伴冰雹", "⛈️"),
}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _qweather_icon(code: str) -> str:
    try:
        value = int(code)
    except ValueError:
        return "🌤️"
    if value == 100:
        return "☀️"
    if 101 <= value <= 103:
        return "🌤️"
    if value in {104, 150, 151, 152, 153}:
        return "☁️"
    if 300 <= value < 400:
        return "⛈️" if value in {302, 303, 304} else "🌧️"
    if 400 <= value < 500:
        return "❄️"
    if 500 <= value < 600:
        return "🌫️"
    return "🌤️"


class OpenMeteoProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client

    async def fetch_daily(self, latitude: Decimal, longitude: Decimal) -> list[DailyWeatherForecast]:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.get(
                self.settings.open_meteo_api_url,
                params={
                    "latitude": str(latitude),
                    "longitude": str(longitude),
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                    "timezone": self.settings.app_timezone,
                    "forecast_days": 2,
                },
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        codes = daily.get("weather_code") or []
        minimums = daily.get("temperature_2m_min") or []
        maximums = daily.get("temperature_2m_max") or []
        if not dates or not (len(dates) == len(codes) == len(minimums) == len(maximums)):
            raise ValueError("Open-Meteo 返回的 daily 数据不完整")
        forecasts = []
        for day, code, minimum, maximum in zip(dates, codes, minimums, maximums, strict=True):
            weather_code = int(code)
            text, icon = WMO_WEATHER.get(weather_code, ("天气变化", "🌤️"))
            forecasts.append(
                DailyWeatherForecast(
                    forecast_date=date.fromisoformat(str(day)),
                    temperature_min=_decimal(minimum),
                    temperature_max=_decimal(maximum),
                    weather_code=str(weather_code),
                    weather_text=text,
                    icon=icon,
                    provider="open_meteo",
                )
            )
        return forecasts


class QWeatherProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client

    async def fetch_daily(self, latitude: Decimal, longitude: Decimal) -> list[DailyWeatherForecast]:
        host = (self.settings.qweather_api_host or "").strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        url = f"{host}/weather/v1/daily/{latitude}/{longitude}"
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.get(
                url,
                params={"days": 2},
                headers={"X-QW-Api-Key": self.settings.qweather_api_key or ""},
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()
        days = payload.get("days") or payload.get("daily") or []
        if not days:
            raise ValueError("和风天气返回的 days 数据为空")
        forecasts = []
        for item in days[:2]:
            daytime = item.get("daytime") or {}
            condition = daytime.get("condition") or {}
            maximum = item.get("temperatureMax") or {}
            minimum = item.get("temperatureMin") or {}
            code = str(condition.get("code") or item.get("iconDay") or "")
            text = str(condition.get("text") or item.get("textDay") or "天气变化")
            forecasts.append(
                DailyWeatherForecast(
                    forecast_date=date.fromisoformat(str(item.get("forecastDate") or item.get("fxDate"))),
                    temperature_min=_decimal(minimum.get("value", item.get("tempMin"))),
                    temperature_max=_decimal(maximum.get("value", item.get("tempMax"))),
                    weather_code=code,
                    weather_text=text,
                    icon=_qweather_icon(code),
                    provider="qweather",
                )
            )
        return forecasts


def create_weather_provider(settings: Settings, client: httpx.AsyncClient | None = None) -> WeatherProvider:
    if settings.weather_provider == "qweather":
        return QWeatherProvider(settings, client)
    return OpenMeteoProvider(settings, client)
