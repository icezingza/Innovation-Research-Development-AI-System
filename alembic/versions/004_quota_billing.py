"""Create billing tables: subscription_plans, tenant_subscriptions, usage_events

Revision ID: 004
Revises: 003
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
import uuid
from datetime import datetime, timezone

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def upgrade() -> None:
    # Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("max_workflows", sa.Integer(), nullable=True),
        sa.Column("max_hypotheses", sa.Integer(), nullable=True),
        sa.Column("max_api_calls", sa.Integer(), nullable=True),
        sa.Column("price_usd_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_subscription_plans_name"),
    )

    # Create tenant_subscriptions table
    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("subscription_plans.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant_id"),
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"]
    )

    # Create usage_events table
    op.create_table(
        "usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_tenant_period", "usage_events", ["tenant_id", "recorded_at"]
    )

    # Seed subscription plans
    plans = [
        (_uuid(), "free", "Free", 10, 100, 1000, 0),
        (_uuid(), "pro", "Pro", 100, 1000, 10000, 4900),
        (_uuid(), "enterprise", "Enterprise", None, None, None, 0),
    ]

    for plan_id, name, display_name, max_wf, max_hyp, max_api, price in plans:
        # Build the VALUES clause with proper NULL handling
        max_wf_val = str(max_wf) if max_wf is not None else "NULL"
        max_hyp_val = str(max_hyp) if max_hyp is not None else "NULL"
        max_api_val = str(max_api) if max_api is not None else "NULL"

        op.execute(
            f"INSERT INTO subscription_plans "
            f"(id, name, display_name, max_workflows, max_hypotheses, max_api_calls, price_usd_cents) "
            f"VALUES ('{plan_id}', '{name}', '{display_name}', {max_wf_val}, {max_hyp_val}, {max_api_val}, {price})"
        )


def downgrade() -> None:
    op.drop_index("ix_usage_tenant_period", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index(
        "ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions"
    )
    op.drop_table("tenant_subscriptions")
    op.drop_table("subscription_plans")
