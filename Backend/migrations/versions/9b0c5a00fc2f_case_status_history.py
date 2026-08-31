"""case status history

case_assignments jaisi hi ek nayi table. created_at pe wahi autogenerate wali
galti dobara aayi thi - src.database.UTCDateTime() bina src import kiye - to
yahan bhi sa.DateTime(timezone=True) hai, jaisa baaki migrations me.

Revision ID: 9b0c5a00fc2f
Revises: 6cadda1b38cc
Create Date: 2026-08-28 10:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b0c5a00fc2f'
down_revision: Union[str, Sequence[str], None] = '6cadda1b38cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'case_status_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        # null = case abhi bana hai, ye transition nahi shuruaat hai.
        sa.Column('from_status', sa.String(), nullable=True),
        sa.Column('to_status', sa.String(), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['changed_by_id'], ['staff.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('case_status_changes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_case_status_changes_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_case_status_changes_id'), ['id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('case_status_changes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_case_status_changes_id'))
        batch_op.drop_index(batch_op.f('ix_case_status_changes_case_id'))

    op.drop_table('case_status_changes')
