"""token version and foreign key indexes

Do cheezein, dono chhoti:

1. staff.token_version - password badalne pe purane token bekaar karne ke liye.
   Purani rows ko 1 milta hai (server_default), warna NOT NULL column khaali
   reh jaata aur migration hi fail ho jaati.

2. Har foreign key pe ek index. Pehle sirf primary key pe index the, jo SQLite
   khud hi banata hai - yaani ek bhi kaam ka index nahi tha. Har list query
   "mera kaunsa hai" foreign key se poochti hai (staff_id, client_id, case_id),
   to bina index ke wo poori table padhti thi. US-20 isi ke baare me hai.

Revision ID: b1c2d3e4f5a6
Revises: 4132736cf266
Create Date: 2026-08-29 13:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "4132736cf266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# index ka naam -> (table, column). Ek hi jagah likha hai, to upgrade aur
# downgrade dono isi list se chalte hain aur aapas me kabhi alag nahi hote.
INDEXES = [
    ("ix_clients_staff_id", "clients", "staff_id"),
    ("ix_cases_client_id", "cases", "client_id"),
    ("ix_cases_staff_id", "cases", "staff_id"),
    ("ix_cases_assignee_id", "cases", "assignee_id"),
    ("ix_notes_case_id", "notes", "case_id"),
    ("ix_notes_staff_id", "notes", "staff_id"),
]


def upgrade() -> None:
    # Do alag batch block, ek nahi. SQLite me batch ka matlab hai "nayi table
    # banao, data copy karo, purani hatao". Ek hi block me column jodna aur
    # phir usi column ko badalna - dono ek saath replay hote hain, aur copy
    # wali INSERT us column ko jaanti hi nahi. Alag alag karne se pehla block
    # poora ho jaata hai, aur doosra ek maujood column pe chalta hai.
    with op.batch_alter_table("staff", schema=None) as batch_op:
        # server_default sirf isliye hai ki jo rows pehle se hain unme kuch to
        # jaye - NOT NULL column khaali nahi chhoda ja sakta.
        batch_op.add_column(
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )

    with op.batch_alter_table("staff", schema=None) as batch_op:
        # Ab server_default hata do, kyunki model me default Python me hai
        # (default=1), server pe nahi. Dono ka schema ek jaisa rehna chahiye,
        # warna test_migrations pakad leta hai. Wahi tareeka jo timestamps
        # wali migration (4be221afd609) me hai.
        batch_op.alter_column(
            "token_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=None,
        )

    for name, table, column in INDEXES:
        op.create_index(name, table, [column], unique=False)


def downgrade() -> None:
    for name, table, column in reversed(INDEXES):
        op.drop_index(name, table_name=table)

    with op.batch_alter_table("staff", schema=None) as batch_op:
        batch_op.drop_column("token_version")
