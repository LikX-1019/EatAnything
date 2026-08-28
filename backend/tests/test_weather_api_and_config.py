from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.v1.admin_management import SchoolCreate, SchoolUpdate
from app.api.v1.users import current_school_weather
from app.core.errors import ApiError
from app.services.weather import invalidate_school_weather
from app.workers import weather as weather_worker
from app.workers.weather import refresh_window_start


class WeatherSession:
    def __init__(self, school=None, weather=None) -> None:
        self.school = school
        self.weather = weather

    async def get(self, _model, _key):
        return self.school

    async def scalar(self, _query):
        return self.weather


def request() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(request_id="weather-test"))


def school(latitude=Decimal("30.460717"), longitude=Decimal("114.268004")) -> SimpleNamespace:
    return SimpleNamespace(id=2, status="active", latitude=latitude, longitude=longitude)


def weather() -> SimpleNamespace:
    return SimpleNamespace(
        forecast_date=date(2026, 8, 28),
        temperature_min=Decimal("25.00"),
        temperature_max=Decimal("33.50"),
        weather_code="2",
        weather_text="多云",
        icon="⛅",
        fetched_at=datetime(2026, 8, 28, 6, tzinfo=UTC),
        provider="open_meteo",
    )


@pytest.mark.asyncio
async def test_weather_api_returns_current_school_cache() -> None:
    result = await current_school_weather(
        request(),
        SimpleNamespace(school_id=2),
        WeatherSession(school(), weather()),
        SimpleNamespace(app_timezone="Asia/Shanghai"),
    )
    assert result["data"]["school_id"] == "2"
    assert result["data"]["temperature_min"] == 25.0
    assert result["data"]["source"] == "open_meteo"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user", "session", "code"),
    [
        (SimpleNamespace(school_id=None), WeatherSession(), "SCHOOL_NOT_SELECTED"),
        (
            SimpleNamespace(school_id=2),
            WeatherSession(school(latitude=None, longitude=None)),
            "SCHOOL_COORDINATES_MISSING",
        ),
        (SimpleNamespace(school_id=2), WeatherSession(school(), None), "WEATHER_NOT_READY"),
    ],
)
async def test_weather_api_reports_explicit_auxiliary_errors(user, session, code) -> None:
    with pytest.raises(ApiError) as captured:
        await current_school_weather(
            request(), user, session, SimpleNamespace(app_timezone="Asia/Shanghai")
        )
    assert captured.value.code == code


def test_school_coordinates_must_be_paired_and_in_range() -> None:
    with pytest.raises(ValidationError):
        SchoolCreate(schoolCode="test", name="测试学校", latitude=30)
    with pytest.raises(ValidationError):
        SchoolCreate(schoolCode="test", name="测试学校", latitude=91, longitude=114)
    with pytest.raises(ValidationError):
        SchoolUpdate(latitude=None)
    update = SchoolUpdate(latitude=None, longitude=None)
    assert update.latitude is None and update.longitude is None


def test_refresh_window_changes_at_six_in_shanghai() -> None:
    before = refresh_window_start(datetime(2026, 8, 28, 21, 59, tzinfo=UTC))
    after = refresh_window_start(datetime(2026, 8, 28, 22, 0, tzinfo=UTC))
    assert before == datetime(2026, 8, 27, 22, 0, tzinfo=UTC)
    assert after == datetime(2026, 8, 28, 22, 0, tzinfo=UTC)


class ExecuteSession:
    def __init__(self) -> None:
        self.statements = []

    async def execute(self, statement) -> None:
        self.statements.append(statement)


@pytest.mark.asyncio
async def test_coordinate_change_invalidation_only_deletes_current_and_future_cache() -> None:
    session = ExecuteSession()
    await invalidate_school_weather(session, 2, "Asia/Shanghai")  # type: ignore[arg-type]
    sql = str(session.statements[0])
    assert "school_weather_daily.school_id" in sql
    assert "school_weather_daily.forecast_date >=" in sql


class ScalarRows:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return self.rows


class WorkerSession:
    def __init__(self, schools) -> None:
        self.schools = schools
        self.rollback_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def scalars(self, _query):
        return ScalarRows(self.schools)

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_worker_skips_missing_coordinates_and_retries_failures(monkeypatch) -> None:
    schools = [school(), SimpleNamespace(id=3, status="active", latitude=None, longitude=None)]
    session = WorkerSession(schools)
    calls: list[int] = []

    async def needs(*_args, **_kwargs):
        return True

    async def refresh(_session, selected, *_args, **_kwargs):
        calls.append(selected.id)
        raise RuntimeError("provider failed")

    monkeypatch.setattr(weather_worker, "SessionFactory", lambda: session)
    monkeypatch.setattr(weather_worker, "school_needs_weather", needs)
    monkeypatch.setattr(weather_worker, "refresh_school_weather", refresh)

    refreshed, failed = await weather_worker.refresh_schools()

    assert refreshed == 0
    assert failed == 1
    assert calls == [2]
    assert session.rollback_count == 1
