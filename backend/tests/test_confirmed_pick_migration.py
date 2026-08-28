import importlib.util
from pathlib import Path
from types import ModuleType


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "0010_confirmed_pick_history.py"
)


class MigrationOperations:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def execute(self, statement: str) -> None:
        self.calls.append(("execute", statement))

    def create_check_constraint(self, name: str, table: str, condition: str) -> None:
        self.calls.append(("create", name, table, condition))

    def drop_constraint(self, name: str, table: str, *, type_: str) -> None:
        self.calls.append(("drop", name, table, type_))


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("confirmed_pick_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_allows_confirmed_pick_and_keeps_legacy_actions() -> None:
    migration = load_migration()
    operations = MigrationOperations()
    migration.op = operations

    migration.upgrade()

    assert (
        "create",
        "ck_activity_history_action",
        "activity_history",
        "action IN ('random_pick', 'store_view', 'confirmed_pick')",
    ) in operations.calls
    assert any("activity_history_action_check" in call[1] for call in operations.calls if call[0] == "execute")


def test_downgrade_converts_confirmed_pick_before_restoring_old_constraint() -> None:
    migration = load_migration()
    operations = MigrationOperations()
    migration.op = operations

    migration.downgrade()

    assert "WHERE action = 'confirmed_pick'" in operations.calls[0][1]
    assert operations.calls[-1] == (
        "create",
        "activity_history_action_check",
        "activity_history",
        "action IN ('random_pick', 'store_view')",
    )
