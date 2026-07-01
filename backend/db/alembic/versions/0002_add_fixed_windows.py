"""add schedules.fixed_windows_json

Stores each optimization's fixed-appliance usage windows so the schedule (and the
Gantt's fixed-appliance hours) can be fully rehydrated after a page reload.

Revision ID: b1f2c3d4e5a6
Revises: ba6d6fec23e8
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1f2c3d4e5a6"
down_revision: Union[str, None] = "ba6d6fec23e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.add_column(sa.Column("fixed_windows_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.drop_column("fixed_windows_json")
