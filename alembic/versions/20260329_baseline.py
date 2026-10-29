"""baseline

Revision ID: 20260329_baseline
Revises:
Create Date: 2026-03-29

"""

from collections.abc import Sequence

revision: str = "20260329_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
