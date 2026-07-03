"""add appliances.group_name

Tên nhóm hiển thị cho thiết bị "Cố định · tự lên lịch" khai nhiều khung giờ trong cùng
một lần thêm — mỗi khung là một row riêng (distinct name), cùng group_name để UI gom lại.
Thuần hiển thị: KHÔNG được đọc bởi logic lập lịch/QUBO. Nullable: thiết bị cũ và thiết bị
chỉ có 1 khung giờ để null (hiển thị phẳng).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.add_column(sa.Column("group_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.drop_column("group_name")
