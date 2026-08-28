import importlib.util
from pathlib import Path
from types import ModuleType


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0011_school_weather_daily.py"
)


class MigrationOperations:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("school_weather_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_creates_weather_cache_and_backfills_wtbu_coordinates() -> None:
    migration = load_migration()
    operations = MigrationOperations()
    migration.op = operations

    migration.upgrade()

    combined = "\n".join(operations.statements)
    assert "CREATE TABLE IF NOT EXISTS school_weather_daily" in combined
    assert "UNIQUE (school_id, forecast_date)" in combined
    assert "temperature_min <= temperature_max" in combined
    assert "provider IN ('open_meteo', 'qweather')" in combined
    assert "latitude = 30.460717" in combined
    assert "longitude = 114.268004" in combined
    assert "school_code = 'wtbu'" in combined


def test_downgrade_drops_cache_and_only_reverts_matching_coordinates() -> None:
    migration = load_migration()
    operations = MigrationOperations()
    migration.op = operations

    migration.downgrade()

    combined = "\n".join(operations.statements)
    assert "DROP TABLE IF EXISTS school_weather_daily" in combined
    assert "latitude = 30.460717" in combined
    assert "longitude = 114.268004" in combined
