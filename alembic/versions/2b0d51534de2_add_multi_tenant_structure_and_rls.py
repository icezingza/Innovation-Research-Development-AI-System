"""add_multi_tenant_structure_and_rls

Revision ID: 2b0d51534de2
Revises: 5fff0a80d7a2
Create Date: 2026-05-16 09:04:46.703558

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b0d51534de2"
down_revision: Union[str, None] = "5fff0a80d7a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. สร้างตาราง tenants
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), unique=True),
        sa.Column("tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("db_connection_string", sa.Text()),
        sa.Column("encrypted_settings", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    # 2. สร้างตาราง users
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.UniqueConstraint("tenant_id", "email"),
    )

    # 3. สร้างตาราง api_keys
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id")),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("prefix", sa.String(8)),
        sa.Column("permissions", sa.JSON()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # 4. สร้างตาราง subscriptions
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("plan_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("payment_method", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    # 5. สร้างตาราง tenant_usage
    op.create_table(
        "tenant_usage",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("units_consumed", sa.BigInteger(), server_default="0"),
        sa.PrimaryKeyConstraint("tenant_id", "date", "metric_name"),
    )

    # 6. เพิ่ม tenant_id เข้าตาราง projects (ถ้ามี) หรือสร้างตารางใหม่
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON()),
    )

    # 7. เปิดใช้งาน RLS บน projects
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON projects
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id')::UUID);
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON projects;")
    op.drop_table("projects")
    op.drop_table("tenant_usage")
    op.drop_table("subscriptions")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("tenants")
