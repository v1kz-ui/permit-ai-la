"""Add cultural_affairs and urban_forestry to clearance_department enum.

Revision ID: 002
Revises: 001
Create Date: 2026-04-02
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DOT already exists in the enum from 001_initial_schema.
    # Add the two new department values.
    op.execute("ALTER TYPE clearance_department ADD VALUE IF NOT EXISTS 'cultural_affairs'")
    op.execute("ALTER TYPE clearance_department ADD VALUE IF NOT EXISTS 'urban_forestry'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # To fully downgrade, recreate the enum (not implemented here as it
    # requires migrating all data out of the column first).
    pass
