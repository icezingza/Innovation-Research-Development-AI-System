"""Add tenant_id to existing tables for row-level tenant isolation

Revision ID: 003
Revises: 002
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000001"

TABLES_TO_MIGRATE = [
    "research_tasks",
    "workflow_records",
    "hypothesis_records",
    "reasoning_traces",
]


def upgrade() -> None:
    for table in TABLES_TO_MIGRATE:
        # Step 1: add nullable column (allows existing rows to exist temporarily)
        op.add_column(
            table,
            sa.Column("tenant_id", sa.String(36), nullable=True),
        )
        # Step 2: backfill existing rows with system tenant
        op.execute(
            f"UPDATE {table} SET tenant_id = '{SYSTEM_TENANT_ID}' WHERE tenant_id IS NULL"
        )
        # Step 3: add FK constraint
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        # Step 4: make NOT NULL now that all rows are backfilled
        op.alter_column(table, "tenant_id", nullable=False)
        # Step 5: index for fast per-tenant queries
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    for table in reversed(TABLES_TO_MIGRATE):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
