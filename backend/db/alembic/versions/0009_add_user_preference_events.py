"""add user_preference_events table

Ghi lại mỗi lần /optimize chạy thành công: trọng số đa mục tiêu (slider w_cost/w_comfort/
w_solar) người dùng chọn + tóm tắt kết quả (num_variables, energy) — tiền đề dữ liệu hành vi
cho tự động hóa Smart Home sau này. `accepted` mặc định True (server_default "1"); ý nghĩa
tinh chỉnh sau (vd đánh dấu False nếu user tối ưu lại ngay sau đó).

CHƯA áp dụng lên DB nào — chỉ tạo migration file theo yêu cầu.

Revision ID: d0e1f2a3b4c5
Revises: b8c9d0e1f2a3
Create Date: 2026-07-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_preference_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("w_cost", sa.Float(), nullable=False),
        sa.Column("w_comfort", sa.Float(), nullable=False),
        sa.Column("w_solar", sa.Float(), nullable=False),
        sa.Column("num_variables", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Float(), nullable=False),
        sa.Column("accepted", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("user_preference_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_preference_events_id"), ["id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("user_preference_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_preference_events_id"))
    op.drop_table("user_preference_events")
