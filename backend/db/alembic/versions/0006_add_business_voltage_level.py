"""add business_profiles.voltage_level

Cấp điện áp đấu nối của doanh nghiệp — chọn cột giá trong biểu giá EVN doanh nghiệp
(business_calc.EVN_BUSINESS_TIERS: "tren_110kv", "22_den_110kv", "6_den_22kv",
"duoi_6kv"). Nullable: tài khoản business tạo trước khi có field này fallback về
"duoi_6kv" khi tính bill.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("business_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("voltage_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("business_profiles", schema=None) as batch_op:
        batch_op.drop_column("voltage_level")
