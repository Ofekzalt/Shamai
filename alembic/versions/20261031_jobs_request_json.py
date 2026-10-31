"""jobs request_json for idempotent enqueue

Revision ID: 20261031_jobs_request_json
Revises: 20261029_geocode_neighborhood
Create Date: 2026-10-31 16:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261031_jobs_request_json"
down_revision: str | Sequence[str] | None = "20261029_geocode_neighborhood"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "request_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("jobs", "request_json", server_default=None)


def downgrade() -> None:
    op.drop_column("jobs", "request_json")
