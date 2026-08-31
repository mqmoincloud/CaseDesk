"""case assignment history

Ek nayi table, koi purani row nahi chhedi jaati - isliye ye seedhi migration
hai. Autogenerate ne created_at ke liye src.database.UTCDateTime() likha tha
bina wo import kiye, jisse file chalti hi nahi. Yahan sa.DateTime(timezone=True)
hai, jaisa baaki migrations me hai: UTCDateTime uske upar sirf ek Python wrapper
hai, DDL dono ka bilkul ek jaisa banta hai.

Revision ID: 6cadda1b38cc
Revises: 10b8ff2754fa
Create Date: 2026-08-28 09:28:08.990052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cadda1b38cc'
down_revision: Union[str, Sequence[str], None] = '10b8ff2754fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'case_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        # null = assignee hata diya gaya. Unassign bhi ek event hai.
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['staff.id'], ),
        sa.ForeignKeyConstraint(['assignee_id'], ['staff.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('case_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_case_assignments_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_case_assignments_id'), ['id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('case_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_case_assignments_id'))
        batch_op.drop_index(batch_op.f('ix_case_assignments_case_id'))

    op.drop_table('case_assignments')
