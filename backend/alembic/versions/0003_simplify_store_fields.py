"""simplify store details and add store area

Revision ID: 0003_store_area
Revises: 0002_schools
"""

from alembic import op


revision = "0003_store_area"
down_revision = "0002_schools"
branch_labels = None
depends_on = None


def _create_catalog_view() -> None:
    op.execute("DROP VIEW IF EXISTS store_catalog")
    op.execute(
        """
        CREATE VIEW store_catalog AS
        SELECT
            s.id,
            s.slug,
            s.school_id,
            sc.school_code,
            sc.name AS school_name,
            s.name,
            s.description,
            s.city,
            s.district,
            s.address,
            s.area,
            COALESCE(STRING_AGG(DISTINCT c.name, ' / ' ORDER BY c.name), '') AS categories,
            ROUND(COALESCE(AVG(r.rating), 0)::NUMERIC, 1) AS score,
            COUNT(DISTINCT r.id) AS review_count,
            m.bucket AS image_bucket,
            m.object_key AS image_object_key
        FROM stores s
        LEFT JOIN schools sc ON sc.id = s.school_id
        LEFT JOIN store_category_links scl ON scl.store_id = s.id
        LEFT JOIN store_categories c ON c.id = scl.category_id
        LEFT JOIN reviews r ON r.store_id = s.id AND r.status = 'published'
        LEFT JOIN store_images si ON si.store_id = s.id AND si.is_primary
        LEFT JOIN media_objects m ON m.id = si.media_id
        WHERE s.status = 'active'
        GROUP BY s.id, sc.school_code, sc.name, m.bucket, m.object_key
        """
    )


def upgrade() -> None:
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS area VARCHAR(100) NOT NULL DEFAULT ''")
    op.execute(
        "UPDATE stores SET area = COALESCE(NULLIF(district, ''), '未分类区域') WHERE area = '' OR area IS NULL"
    )
    for column in ("latitude", "longitude", "phone", "average_price", "business_hours"):
        op.execute(f"ALTER TABLE stores DROP COLUMN IF EXISTS {column}")
    _create_catalog_view()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS store_catalog")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS latitude NUMERIC(9, 6)")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS longitude NUMERIC(9, 6)")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS phone VARCHAR(40)")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS average_price NUMERIC(10, 2)")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS business_hours JSONB NOT NULL DEFAULT '{}'::JSONB")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS area")
