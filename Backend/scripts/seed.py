"""Demo data for CaseDesk (NF-04).

Run with:  python -m scripts.seed

Wipes every row first, so running it twice gives the same result both times.
No random values anywhere - the data must be identical on every machine,
otherwise a test that passes today fails tomorrow for no visible reason.
"""

from datetime import datetime, timezone

from src.database import localSession
from src.models import Case, Client, Note, Staff
from src.security import hash_password

# Same password for both accounts - this is demo data, not a real deployment.
SEED_PASSWORD = "password123"

# Domain must be one EmailStr accepts - reserved TLDs like .test are rejected
# by email-validator, and these accounts have to survive a real login.
STAFF = [
    {"name": "Ali Khan", "email": "ali@casedesk.example.com"},
    {"name": "Sara Sheikh", "email": "sara@casedesk.example.com"},
]

# Repeated on purpose so a search for "Kumar" or "Priya" returns several rows.
FIRST_NAMES = [
    "Ramesh", "Priya", "Suresh", "Anita", "Mahesh",
    "Kavita", "Rajesh", "Sunita", "Dinesh", "Lalita",
]
LAST_NAMES = ["Kumar", "Sharma", "Patel", "Verma", "Singh"]

CITIES = ["Delhi", "Mumbai", "Pune", "Jaipur", "Lucknow"]

CASE_TYPES = ["Civil", "Criminal", "Family", "Property", "Labour"]

# Every status appears, so the US-11 status filter has something to filter.
STATUSES = ["Intake", "Active", "Settled", "Closed"]

NOTE_BODIES = [
    "Initial consultation done. Client briefed on the process.",
    "Documents collected and filed.",
    "Called the client for a status update.",
    "Hearing date confirmed with the court.",
    "Opposing counsel requested an extension.",
]

# Ali gets enough clients to page through; Sara gets a smaller, different
# number so an isolation bug shows up as a wrong count rather than a match.
ALI_CLIENT_COUNT = 65
SARA_CLIENT_COUNT = 20

# Two of Ali's clients start out soft-deleted, so US-16 can be checked
# without having to delete anything by hand first.
SOFT_DELETED_INDEXES = {7, 23}


def wipe(db):
    """Delete every row, children first so no foreign key is left dangling."""
    db.query(Note).delete()
    db.query(Case).delete()
    db.query(Client).delete()
    db.query(Staff).delete()
    db.commit()


def make_staff(db):
    created = []
    for entry in STAFF:
        staff = Staff(
            name=entry["name"],
            email=entry["email"],
            password_hash=hash_password(SEED_PASSWORD),
        )
        db.add(staff)
        created.append(staff)
    db.commit()
    for staff in created:
        db.refresh(staff)
    return created


def make_clients(db, staff, count, soft_delete_indexes=frozenset()):
    clients = []
    for i in range(count):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        client = Client(
            staff_id=staff.id,
            name=f"{first} {last}",
            # staff.id is in the address on purpose: if two staff shared an
            # address, an isolation test that searches for one would match the
            # other's client and look like a leak that isn't there.
            email=f"{first.lower()}.{last.lower()}{staff.id}{i:03d}@example.com",
            phone=f"98{staff.id:02d}{i:06d}",
            address=f"{i + 1} Main Road, {CITIES[i % len(CITIES)]}",
        )
        if i in soft_delete_indexes:
            client.deleted_at = datetime.now(timezone.utc)
        db.add(client)
        clients.append(client)
    db.commit()
    for client in clients:
        db.refresh(client)
    return clients


def make_cases(db, clients, owner, other_staff, count):
    """One case each for the first `count` live clients."""
    live = [c for c in clients if c.deleted_at is None][:count]
    cases = []
    for i, client in enumerate(live):
        # Cycles owner -> other staff -> unassigned, so the assignee filter
        # has all three situations to deal with.
        assignee_id = [owner.id, other_staff.id, None][i % 3]
        case = Case(
            client_id=client.id,
            staff_id=owner.id,
            assignee_id=assignee_id,
            title=f"{CASE_TYPES[i % len(CASE_TYPES)]} matter for {client.name}",
            case_type=CASE_TYPES[i % len(CASE_TYPES)],
            status=STATUSES[i % len(STATUSES)],
        )
        db.add(case)
        cases.append(case)
    db.commit()
    for case in cases:
        db.refresh(case)
    return cases


def make_notes(db, cases, author):
    notes = []
    for i, case in enumerate(cases):
        for j in range(2):
            notes.append(
                Note(
                    case_id=case.id,
                    staff_id=author.id,
                    body=NOTE_BODIES[(i + j) % len(NOTE_BODIES)],
                )
            )
    db.add_all(notes)
    db.commit()
    return notes


def seed():
    db = localSession()
    try:
        wipe(db)

        ali, sara = make_staff(db)

        ali_clients = make_clients(db, ali, ALI_CLIENT_COUNT, SOFT_DELETED_INDEXES)
        sara_clients = make_clients(db, sara, SARA_CLIENT_COUNT)

        ali_cases = make_cases(db, ali_clients, ali, sara, count=30)
        sara_cases = make_cases(db, sara_clients, sara, ali, count=10)

        ali_notes = make_notes(db, ali_cases, ali)
        sara_notes = make_notes(db, sara_cases, sara)

        live_ali = ALI_CLIENT_COUNT - len(SOFT_DELETED_INDEXES)
        total = (
            len(STAFF)
            + ALI_CLIENT_COUNT
            + SARA_CLIENT_COUNT
            + len(ali_cases)
            + len(sara_cases)
            + len(ali_notes)
            + len(sara_notes)
        )

        print("Seeded CaseDesk demo data")
        print(f"  staff    : {len(STAFF)}")
        print(f"  clients  : {ALI_CLIENT_COUNT + SARA_CLIENT_COUNT} "
              f"({live_ali} live + {len(SOFT_DELETED_INDEXES)} soft-deleted for Ali, "
              f"{SARA_CLIENT_COUNT} for Sara)")
        print(f"  cases    : {len(ali_cases) + len(sara_cases)}")
        print(f"  notes    : {len(ali_notes) + len(sara_notes)}")
        print(f"  total    : {total} rows")
        print()
        print("Log in with either account, password is the same for both:")
        for entry in STAFF:
            print(f"  {entry['email']}  /  {SEED_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
