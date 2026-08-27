"""utc aware timestamps

The column type does not change - UTCDateTime still compiles to DATETIME on
SQLite. What changes is where the default comes from. The models used to carry
server_default=func.now(), which is SQLite's own CURRENT_TIMESTAMP and never
passes through Python, so it skipped the UTC conversion entirely. Defaults are
now set in Python (default=utcnow), so the server defaults are dropped here to
keep the schema and the models saying the same thing.

Alembic does not notice this on its own - it only compares server defaults when
compare_server_default is turned on - so this migration is written by hand.

Revision ID: 4be221afd609
Revises: 7d1bc644d935
Create Date: 2026-08-27 10:50:09.137788

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4be221afd609"
down_revision: Union[str, Sequence[str], None] = "7d1bc644d935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# table -> the timestamp columns on it that had a server default
TIMESTAMP_COLUMNS = {
    "staff": ["created_at", "updated_at"],
    "clients": ["created_at", "updated_at"],
    "cases": ["created_at", "updated_at"],
    "notes": ["created_at"],
}


def upgrade() -> None:
    for table, columns in TIMESTAMP_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.DateTime(),
                    existing_nullable=False,
                    server_default=None,
                )


def downgrade() -> None:
    for table, columns in TIMESTAMP_COLUMNS.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.DateTime(),
                    existing_nullable=False,
                    server_default=sa.text("(CURRENT_TIMESTAMP)"),
                )
