"""add staff role

Revision ID: 10b8ff2754fa
Revises: 4be221afd609
Create Date: 2026-08-27 16:06:59.651889

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10b8ff2754fa'
down_revision: Union[str, Sequence[str], None] = '4be221afd609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default is needed here even though the model does not carry one:
    # the column is NOT NULL, and rows that already exist have to be given a
    # value as the column is added. It is dropped straight afterwards so the
    # schema matches the model, which sets the default in Python instead.
    with op.batch_alter_table("staff", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(), nullable=False, server_default="staff")
        )

    with op.batch_alter_table("staff", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("staff", schema=None) as batch_op:
        batch_op.drop_column("role")
