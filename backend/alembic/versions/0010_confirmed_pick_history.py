"""允许记录用户确认选店历史。"""

from alembic import op


revision = "0010_confirmed_pick_history"
down_revision = "0009_add_user_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 兼容 baseline 自动生成的旧约束名，以及重复初始化时可能存在的新约束名。
    op.execute(
        "ALTER TABLE activity_history "
        "DROP CONSTRAINT IF EXISTS activity_history_action_check"
    )
    op.execute(
        "ALTER TABLE activity_history "
        "DROP CONSTRAINT IF EXISTS ck_activity_history_action"
    )
    op.create_check_constraint(
        "ck_activity_history_action",
        "activity_history",
        "action IN ('random_pick', 'store_view', 'confirmed_pick')",
    )


def downgrade() -> None:
    # 旧版本把同一确认接口记录为 store_view，回退时按旧语义转换已有数据。
    op.execute(
        "UPDATE activity_history SET action = 'store_view' "
        "WHERE action = 'confirmed_pick'"
    )
    op.drop_constraint(
        "ck_activity_history_action",
        "activity_history",
        type_="check",
    )
    op.create_check_constraint(
        "activity_history_action_check",
        "activity_history",
        "action IN ('random_pick', 'store_view')",
    )
