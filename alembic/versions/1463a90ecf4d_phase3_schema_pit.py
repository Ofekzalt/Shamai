"""phase3_schema_pit

Revision ID: 1463a90ecf4d
Revises: 20260329_baseline
Create Date: 2026-10-29 16:43:04.955996

"""

from collections.abc import Sequence

import geoalchemy2.types
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1463a90ecf4d"
down_revision: str | Sequence[str] | None = "20260329_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage_status", sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_evidence_key"),
    )
    op.create_table(
        "geocode_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("street", sa.String(length=256), nullable=False),
        sa.Column("house_number", sa.String(length=32), nullable=False),
        sa.Column("lon", sa.Double(), nullable=False),
        sa.Column("lat", sa.Double(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("street", "house_number", name="uq_geocode_street_house"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_calls_run_id"), "llm_calls", ["run_id"], unique=False)
    op.create_table(
        "planning_area_coverage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("cell_x", sa.Integer(), nullable=False),
        sa.Column("cell_y", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("lease_holder", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "cell_x", "cell_y", name="uq_planning_coverage_cell"),
    )
    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("pl_number", sa.String(length=64), nullable=False),
        sa.Column("mp_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "pl_number", name="uq_plans_source_pl_number"),
    )
    op.create_index("ix_plans_geom", "plans", ["geom"], unique=False, postgresql_using="gist")
    op.create_table(
        "renewal_polygons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_feature_id", sa.String(length=128), nullable=False),
        sa.Column("taba", sa.String(length=128), nullable=True),
        sa.Column("snapshot_status", sa.String(length=128), nullable=True),
        sa.Column("history_available", sa.Boolean(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at_estimated", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "source_feature_id",
            name="uq_renewal_polygons_source_feature",
        ),
    )
    op.create_index(
        op.f("ix_renewal_polygons_available_at"),
        "renewal_polygons",
        ["available_at"],
        unique=False,
    )
    op.create_index(
        "ix_renewal_polygons_geom",
        "renewal_polygons",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_table(
        "statistical_areas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cbs_code", sa.String(length=32), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cbs_code", name="uq_statistical_areas_cbs_code"),
    )
    op.create_index(
        "ix_statistical_areas_geom",
        "statistical_areas",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_table(
        "transaction_area_coverage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("cell_x", sa.Integer(), nullable=False),
        sa.Column("cell_y", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("lease_holder", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "cell_x", "cell_y", name="uq_transaction_coverage_cell"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_row_id", sa.String(length=128), nullable=False),
        sa.Column("price_agorot", sa.BigInteger(), nullable=False),
        sa.Column("size_sqm", sa.Double(), nullable=True),
        sa.Column("rooms", sa.Double(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("neighborhood", sa.String(length=128), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at_estimated", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_row_id", name="uq_transactions_source_row"),
    )
    op.create_index(
        op.f("ix_transactions_available_at"),
        "transactions",
        ["available_at"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_geom",
        "transactions",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_table(
        "plan_status_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at_estimated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "status",
            "effective_at",
            "source",
            name="uq_plan_status_events_natural",
        ),
    )
    op.create_index(
        op.f("ix_plan_status_events_available_at"),
        "plan_status_events",
        ["available_at"],
        unique=False,
    )
    op.create_index(
        "ix_plan_status_events_plan_id",
        "plan_status_events",
        ["plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_plan_status_events_plan_id", table_name="plan_status_events")
    op.drop_index(op.f("ix_plan_status_events_available_at"), table_name="plan_status_events")
    op.drop_table("plan_status_events")
    op.drop_index("ix_transactions_geom", table_name="transactions", postgresql_using="gist")
    op.drop_index(op.f("ix_transactions_available_at"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("transaction_area_coverage")
    op.drop_index(
        "ix_statistical_areas_geom",
        table_name="statistical_areas",
        postgresql_using="gist",
    )
    op.drop_table("statistical_areas")
    op.drop_index(
        "ix_renewal_polygons_geom",
        table_name="renewal_polygons",
        postgresql_using="gist",
    )
    op.drop_index(op.f("ix_renewal_polygons_available_at"), table_name="renewal_polygons")
    op.drop_table("renewal_polygons")
    op.drop_index("ix_plans_geom", table_name="plans", postgresql_using="gist")
    op.drop_table("plans")
    op.drop_table("planning_area_coverage")
    op.drop_index(op.f("ix_llm_calls_run_id"), table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_table("jobs")
    op.drop_table("geocode_cache")
    op.drop_table("evidence")
