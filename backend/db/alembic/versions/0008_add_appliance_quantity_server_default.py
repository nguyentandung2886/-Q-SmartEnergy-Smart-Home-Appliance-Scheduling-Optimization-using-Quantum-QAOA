"""add server_default="1" to appliances.quantity

Cột `appliances.quantity` là NOT NULL nhưng chỉ có default phía Python (`models.py:66`
`default=1`) — INSERT không đi qua ORM (hoặc dữ liệu tạo từ `0001` cũ) có thể thiếu giá trị.
Thêm `server_default="1"` để DB tự điền 1 khi client không cung cấp, khớp với default ORM.

Phạm vi: CHỈ đặt server_default cho row MỚI. KHÔNG backfill NULL/0 hiện có (ngoài phạm vi audit
B9) — code đọc đã phòng thủ `row.quantity if row.quantity else 1`.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            server_default="1",
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("appliances", schema=None) as batch_op:
        batch_op.alter_column(
            "quantity",
            existing_type=sa.Integer(),
            server_default=None,
            existing_nullable=False,
        )
