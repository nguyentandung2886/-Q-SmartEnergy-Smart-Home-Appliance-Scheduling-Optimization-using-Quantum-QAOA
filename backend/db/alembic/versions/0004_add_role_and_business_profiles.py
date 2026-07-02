"""add users.role and business_profiles table

Three account roles: "household" (default), "business", "admin". Businesses get a
1-1 BusinessProfile (production/commercial, scale, contracted power). Admin is
granted only via the seed script — never public signup.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=20), nullable=False, server_default="household")
        )

    op.create_table(
        "business_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("business_type", sa.String(length=20), nullable=False),
        sa.Column("scale", sa.String(length=50), nullable=True),
        sa.Column("contracted_power_kw", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    with op.batch_alter_table("business_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_business_profiles_id"), ["id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("business_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_business_profiles_id"))
    op.drop_table("business_profiles")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")
