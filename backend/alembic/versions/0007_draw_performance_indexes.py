"""增加抽取热路径索引。"""

from alembic import op


revision = "0007_draw_performance_indexes"
down_revision = "0006_admin_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_stores_school_active "
        "ON stores (school_id, id) WHERE status = 'active'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_check_ins_user_store_published "
        "ON check_ins (user_id, store_id) WHERE status = 'published'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_check_ins_user_store_published")
    op.execute("DROP INDEX IF EXISTS idx_stores_school_active")
