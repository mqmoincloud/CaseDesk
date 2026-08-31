"""staff soft delete

Nullable column hai, to purani rows ko bharne ki zaroorat nahi - koi
server_default nahi chahiye. (Autogenerate ne created_at wali wahi galti
dobara ki thi: src.database.UTCDateTime() bina src import kiye.)

Revision ID: 4132736cf266
Revises: 9b0c5a00fc2f
Create Date: 2026-08-28 11:22:16.862895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4132736cf266'
down_revision: Union[str, Sequence[str], None] = '9b0c5a00fc2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
     
    with op.batch_alter_table('staff', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
     
    with op.batch_alter_table('staff', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')

    # ### end Alembic commands ###
