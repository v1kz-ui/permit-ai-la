"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── Users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("angeleno_id", sa.String(100), unique=True, nullable=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("homeowner", "contractor", "architect", "staff", "admin", name="user_role", create_type=True),
            server_default="homeowner",
            nullable=False,
        ),
        sa.Column(
            "language",
            sa.Enum("en", "es", "ko", "zh", "tl", name="language"),
            server_default="en",
            nullable=False,
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("firebase_token", sa.Text, nullable=True),
        sa.Column("notification_push", sa.Boolean, server_default="true"),
        sa.Column("notification_sms", sa.Boolean, server_default="false"),
        sa.Column("notification_email", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Parcels ───────────────────────────────────────────────────────────
    op.create_table(
        "parcels",
        sa.Column("apn", sa.String(20), primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("zone_class", sa.String(20), nullable=True),
        sa.Column("zone_description", sa.String(255), nullable=True),
        sa.Column("land_use", sa.String(100), nullable=True),
        sa.Column("lot_area_sqft", sa.Float, nullable=True),
        sa.Column("lot_width", sa.Float, nullable=True),
        sa.Column("lot_depth", sa.Float, nullable=True),
        sa.Column("is_coastal_zone", sa.Boolean, server_default="false"),
        sa.Column("is_hillside", sa.Boolean, server_default="false"),
        sa.Column("is_very_high_fire_severity", sa.Boolean, server_default="false"),
        sa.Column("is_historic", sa.Boolean, server_default="false"),
        sa.Column("is_flood_zone", sa.Boolean, server_default="false"),
        sa.Column("is_specific_plan", sa.Boolean, server_default="false"),
        sa.Column("specific_plan_name", sa.String(255), nullable=True),
        sa.Column("council_district", sa.Integer, nullable=True),
        sa.Column("neighborhood_council", sa.String(255), nullable=True),
        sa.Column("census_tract", sa.String(20), nullable=True),
        sa.Column("zimas_last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING gist (geom)")

    # ── Projects ──────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("apn", sa.String(20), nullable=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "pathway",
            sa.Enum("eo1_like_for_like", "eo8_expanded", "standard", name="project_pathway"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "intake", "in_review", "approved", "issued",
                "inspection", "final", "closed",
                name="project_status",
            ),
            server_default="intake",
            nullable=False,
        ),
        sa.Column("original_sqft", sa.Float, nullable=True),
        sa.Column("proposed_sqft", sa.Float, nullable=True),
        sa.Column("stories", sa.Integer, nullable=True),
        sa.Column("is_coastal_zone", sa.Boolean, server_default="false"),
        sa.Column("is_hillside", sa.Boolean, server_default="false"),
        sa.Column("is_very_high_fire_severity", sa.Boolean, server_default="false"),
        sa.Column("is_historic", sa.Boolean, server_default="false"),
        sa.Column("is_flood_zone", sa.Boolean, server_default="false"),
        sa.Column("ai_pathway_confidence", sa.Float, nullable=True),
        sa.Column("ai_reasoning", sa.Text, nullable=True),
        sa.Column("predicted_total_days", sa.Integer, nullable=True),
        sa.Column("ladbs_permit_number", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_projects_owner", "projects", ["owner_id"])
    op.create_index("idx_projects_apn", "projects", ["apn"])
    op.create_index("idx_projects_status", "projects", ["status"])

    # ── Clearances ────────────────────────────────────────────────────────
    op.create_table(
        "clearances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "department",
            sa.Enum(
                "ladbs", "dcp", "boe", "lafd", "ladwp", "lasan", "lahd", "dot",
                name="clearance_department",
            ),
            nullable=False,
        ),
        sa.Column("clearance_type", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "not_started", "in_review", "approved", "conditional", "denied",
                name="clearance_status",
            ),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column("is_bottleneck", sa.Boolean, server_default="false"),
        sa.Column("predicted_days", sa.Integer, nullable=True),
        sa.Column("submitted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "conflict_with_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clearances.id"),
            nullable=True,
        ),
        sa.Column("conflict_description", sa.Text, nullable=True),
        sa.Column("pcis_status_raw", sa.String(100), nullable=True),
        sa.Column("pcis_last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_clearances_project", "clearances", ["project_id"])
    op.create_index("idx_clearances_dept_status", "clearances", ["department", "status"])

    # ── Inspections ───────────────────────────────────────────────────────
    op.create_table(
        "inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("inspection_type", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("scheduled", "passed", "failed", "cancelled", name="inspection_status"),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inspector_name", sa.String(255), nullable=True),
        sa.Column("failure_reasons", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_inspections_project", "inspections", ["project_id"])

    # ── Documents ─────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "plans", "permit_application", "insurance", "photos",
                "soils_report", "structural_calc", "title_report", "other",
                name="document_type",
            ),
            nullable=False,
        ),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_documents_project", "documents", ["project_id"])

    # ── Notifications ─────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("push", "sms", "email", name="notification_channel"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
        sa.Column(
            "delivery_status",
            sa.Enum("pending", "sent", "failed", name="delivery_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_notifications_user", "notifications", ["user_id"])
    op.create_index(
        "idx_notifications_payload",
        "notifications",
        ["payload"],
        postgresql_using="gin",
    )

    # ── Audit Log ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_record", "audit_log", ["table_name", "record_id"])
    op.create_index("idx_audit_changed_by", "audit_log", ["changed_by"])
    op.create_index(
        "idx_audit_old_value",
        "audit_log",
        ["old_value"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_audit_new_value",
        "audit_log",
        ["new_value"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("notifications")
    op.drop_table("documents")
    op.drop_table("inspections")
    op.drop_table("clearances")
    op.drop_table("projects")
    op.drop_table("parcels")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "user_role", "language", "project_pathway", "project_status",
        "clearance_department", "clearance_status", "inspection_status",
        "document_type", "notification_channel", "delivery_status",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
