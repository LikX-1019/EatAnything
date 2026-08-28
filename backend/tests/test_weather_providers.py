from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from app.integrations.weather import OpenMeteoProvider, QWeatherProvider


@pytest.mark.asyncio
async def test_open_meteo_provider_normalizes_two_day_forecast() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-08-28", "2026-08-29"],
                    "weather_code": [2, 61],
                    "temperature_2m_min": [25.1, 24],
                    "temperature_2m_max": [33.4, 31],
                }
            },
        )

    settings = SimpleNamespace(
        open_meteo_api_url="https://api.open-meteo.com/v1/forecast",
        app_timezone="Asia/Shanghai",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        forecasts = await OpenMeteoProvider(settings, client).fetch_daily(  # type: ignore[arg-type]
            Decimal("30.460717"), Decimal("114.268004")
        )

    assert len(forecasts) == 2
    assert forecasts[0].weather_text == "多云"
    assert forecasts[0].temperature_min == Decimal("25.10")
    assert forecasts[0].provider == "open_meteo"
    assert captured is not None
    assert captured.url.params["forecast_days"] == "2"
    assert captured.url.params["timezone"] == "Asia/Shanghai"
    assert captured.url.params["latitude"] == "30.460717"
    assert captured.url.params["longitude"] == "114.268004"


@pytest.mark.asyncio
async def test_qweather_provider_uses_host_key_coordinates_and_two_days() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(
            200,
            json={
                "days": [
                    {
                        "forecastDate": "2026-08-28",
                        "temperatureMin": {"value": "25"},
                        "temperatureMax": {"value": "34"},
                        "daytime": {"condition": {"code": "101", "text": "多云"}},
                    },
                    {
                        "forecastDate": "2026-08-29",
                        "temperatureMin": {"value": "24"},
                        "temperatureMax": {"value": "32"},
                        "daytime": {"condition": {"code": "305", "text": "小雨"}},
                    },
                ]
            },
        )

    settings = SimpleNamespace(qweather_api_host="weather.example.test", qweather_api_key="secret")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        forecasts = await QWeatherProvider(settings, client).fetch_daily(  # type: ignore[arg-type]
            Decimal("30.460717"), Decimal("114.268004")
        )

    assert len(forecasts) == 2
    assert forecasts[0].provider == "qweather"
    assert forecasts[1].icon == "🌧️"
    assert captured is not None
    assert captured.url.path == "/weather/v1/daily/30.460717/114.268004"
    assert captured.url.params["days"] == "2"
    assert captured.headers["X-QW-Api-Key"] == "secret"
