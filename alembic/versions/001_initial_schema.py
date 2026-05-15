"""Initial schema: research_tasks, workflow_records, hypothesis_records, reasoning_traces.

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
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
    )

    op.create_table(
        "workflow_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sub_questions", sa.JSON, nullable=True),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "hypothesis_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("evidence", sa.JSON, nullable=True),
        sa.Column("generation", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "reasoning_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("input_hash", sa.String(16), nullable=False),
        sa.Column("output_summary", sa.Text, nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indices for common queries
    op.create_index("ix_hypothesis_topic", "hypothesis_records", ["topic"])
    op.create_index("ix_hypothesis_session", "hypothesis_records", ["session_id"])
    op.create_index("ix_reasoning_operation", "reasoning_traces", ["operation"])
    op.create_index("ix_research_task_status", "research_tasks", ["status"])
    op.create_index("ix_workflow_status", "workflow_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_status")
    op.drop_index("ix_research_task_status")
    op.drop_index("ix_reasoning_operation")
    op.drop_index("ix_hypothesis_session")
    op.drop_index("ix_hypothesis_topic")
    op.drop_table("reasoning_traces")
    op.drop_table("hypothesis_records")
    op.drop_table("workflow_records")
    op.drop_table("research_tasks")
