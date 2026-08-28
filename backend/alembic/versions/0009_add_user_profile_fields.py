"""新增用户性别与生日字段。"""

from alembic import op
import sqlalchemy as sa


revision = "0009_add_user_profile_fields"
down_revision = "0008_platform_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_users", sa.Column("gender", sa.String(length=20), nullable=True))
    op.add_column("app_users", sa.Column("birthday", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_users", "birthday")
    op.drop_column("app_users", "gender")
