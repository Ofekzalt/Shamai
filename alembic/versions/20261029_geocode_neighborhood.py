"""geocode neighborhood for allowlist

Revision ID: 20261029_geocode_neighborhood
Revises: 1463a90ecf4d
Create Date: 2026-10-29 19:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261029_geocode_neighborhood"
down_revision: str | Sequence[str] | None = "1463a90ecf4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("geocode_cache", sa.Column("neighborhood", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("geocode_cache", "neighborhood")
