"""Demo data for CaseDesk (NF-04).

Run with:  python -m scripts.seed

Wipes every row first, so running it twice gives the same result both times.
No random values anywhere - the data must be identical on every machine,
otherwise a test that passes today fails tomorrow for no visible reason.
"""

from datetime import datetime, timedelta, timezone

from src.database import localSession
from src.models import Case, CaseAssignment, CaseStatusChange, Client, Note, Staff
from src.security import hash_password

# Same password for every account - this is demo data, not a real deployment.
SEED_PASSWORD = "password123"

# Domain must be one EmailStr accepts - reserved TLDs like .test are rejected
# by email-validator, and these accounts have to survive a real login.
#
# The admin has to be created here rather than through /auth/register, because
# that route is admin-only: without this row nobody could ever register anyone.
ACCOUNTS = [
    {"name": "Admin", "email": "admin@casedesk.example.com", "role": "admin"},
    {"name": "Ali Khan", "email": "ali@casedesk.example.com", "role": "staff"},
    {"name": "Sara Sheikh", "email": "sara@casedesk.example.com", "role": "staff"},
]

# Every client gets a distinct full name, but first and last names repeat
# across clients - so searching "Priya" or "Kumar" returns several rows
# while no two people are the same. 15 x 8 gives 120 unique pairs,
# comfortably more than the 85 clients seeded below.
FIRST_NAMES = [
    "Ramesh", "Priya", "Suresh", "Anita", "Mahesh",
    "Kavita", "Rajesh", "Sunita", "Dinesh", "Lalita",
    "Farhan", "Meera", "Imran", "Neha", "Vikram",
]
LAST_NAMES = ["Kumar", "Sharma", "Patel", "Verma", "Singh", "Reddy", "Nair", "Khan"]

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


# The seed runs in a single instant, so every event gets its timestamp set by
# hand - otherwise a case's whole journey lands in the same second and the
# timeline is useless. The offsets are fixed, never random: the same shape on
# every machine.
def days_ago(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


# How many days ago case i was opened. Every later event is measured from this.
#
# It counts upwards, not down: case 0 is START_DAYS old and each case after it
# is older still. Counting down would push later cases towards day zero, and
# the status steps below - which subtract further days - would then land in
# the future.
START_DAYS = 30


def opened_days_ago(i):
    return START_DAYS + i


def wipe(db):
    """Delete every row, children first so no foreign key is left dangling."""
    db.query(Note).delete()
    db.query(CaseAssignment).delete()
    db.query(CaseStatusChange).delete()
    db.query(Case).delete()
    db.query(Client).delete()
    db.query(Staff).delete()
    db.commit()


def make_staff(db):
    """Create every account and hand back admin, Ali and Sara in that order.

    The admin owns no clients or cases - it can already see everyone's - but it
    does assign some of them, so the Cases page has both "you assigned" and
    "Admin assigned" to show.
    """
    created = []
    for entry in ACCOUNTS:
        staff = Staff(
            name=entry["name"],
            email=entry["email"],
            role=entry["role"],
            password_hash=hash_password(SEED_PASSWORD),
        )
        db.add(staff)
        created.append(staff)
    db.commit()
    for staff in created:
        db.refresh(staff)

    return created


def make_clients(db, staff, count, soft_delete_indexes=frozenset(), name_offset=0):
    """`count` clients for one staff member, each with a distinct name.

    name_offset starts the two staff at different points in the same name
    list. Without it Ali's first client and Sara's first client would be
    namesakes, because both loops start at i=0.
    """
    combinations = len(FIRST_NAMES) * len(LAST_NAMES)
    if name_offset + count > combinations:
        # Better to stop here than to repeat a name silently. Raising the
        # count means adding names.
        raise ValueError(
            f"need names for {name_offset + count} clients, "
            f"but only {combinations} distinct names can be built"
        )

    clients = []
    for i in range(count):
        n = name_offset + i
        # The first name changes every time; the last name only advances once
        # the first-name list has gone round once, so each pair occurs exactly
        # once.
        first = FIRST_NAMES[n % len(FIRST_NAMES)]
        last = LAST_NAMES[n // len(FIRST_NAMES)]
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


def make_cases(db, clients, owner, other_staff, admin, client_count):
    """Opens cases on `client_count` live clients - not `client_count` cases.

    Each of those clients gets one, two or three cases, so 30 clients produce
    60 cases. More than one case per client is what makes the client detail
    page worth opening, and it lets a single client hold several statuses.

    Clients are picked newest-first and then every `step`-th one, so that
    every part of the list holds a mix of clients with cases and clients
    without. Clients with no cases matter too: they are the only ones a
    delete can succeed on, so without them the 409 path is never visible.

    Assignment and status rows are written here as well. The seed writes
    cases straight to the database rather than through the API, so the
    history the routers would have recorded has to be recorded by hand -
    otherwise every demo case would have no timeline at all.
    """
    alive = [c for c in clients if c.deleted_at is None]
    step = max(1, len(alive) // client_count)
    live = alive[::-1][::step][:client_count]
    cases = []
    # n advances per case created, not per client. That is what puts two cases
    # on the same client at different statuses and different assignees -
    # otherwise every row inside a client would look identical.
    n = 0
    for i, client in enumerate(live):
        for _ in range(1 + i % 3):
            # created_at is set explicitly so the row and its history agree.
            # Left to the column default the case would be dated today while
            # its own timeline said it opened two months ago - a case created
            # after it closed.
            #
            # The assignee cycles owner -> other staff -> unassigned, so the
            # assignee filter has all three situations to deal with.
            assignee_id = [owner.id, other_staff.id, None][n % 3]
            opened = days_ago(opened_days_ago(n))
            case = Case(
                client_id=client.id,
                staff_id=owner.id,
                assignee_id=assignee_id,
                title=f"{CASE_TYPES[n % len(CASE_TYPES)]} matter for {client.name}",
                case_type=CASE_TYPES[n % len(CASE_TYPES)],
                status=STATUSES[n % len(STATUSES)],
                created_at=opened,
                updated_at=opened,
            )
            db.add(case)
            cases.append(case)
            n += 1
    db.commit()
    for case in cases:
        db.refresh(case)

    make_assignments(db, cases, owner, other_staff, admin)
    make_status_changes(db, cases, owner)
    return cases


# The seed writes each case straight to its final status, so the steps that
# would have taken it there are written by hand, starting from Intake.
STATUS_PATH = ["Intake", "Active", "Settled", "Closed"]


def make_status_changes(db, cases, owner):
    """One case's whole journey: opened, then advanced a step at a time."""
    rows = []
    for i, case in enumerate(cases):
        opened = opened_days_ago(i)

        # The case opened at Intake. Not a transition - the starting point.
        rows.append(
            CaseStatusChange(
                case_id=case.id,
                from_status=None,
                to_status=STATUS_PATH[0],
                changed_by_id=owner.id,
                created_at=days_ago(opened),
            )
        )

        # Then Intake to its current status, one row per step - the same path
        # ALLOWED_TRANSITIONS forces in the API.
        reached = STATUS_PATH.index(case.status)
        for step in range(reached):
            rows.append(
                CaseStatusChange(
                    case_id=case.id,
                    from_status=STATUS_PATH[step],
                    to_status=STATUS_PATH[step + 1],
                    changed_by_id=owner.id,
                    # Each step lands five days after the one before it.
                    created_at=days_ago(opened - 5 * (step + 1)),
                )
            )

    db.add_all(rows)
    db.commit()
    return rows


def make_assignments(db, cases, owner, other_staff, admin):
    """Assignment history for the cases that have an assignee.

    The last row always matches the case's current assignee - otherwise the
    page would say one thing and the history another.
    """
    rows = []
    for i, case in enumerate(cases):
        if case.assignee_id is None:
            continue

        # Who did it: sometimes the case's own owner, sometimes the admin on
        # their behalf. Both, so the Cases page shows each wording.
        assigned_by = owner if i % 2 == 0 else admin

        # Every sixth case also gets an earlier spell, so the case page
        # timeline is more than a single line. This row goes first, then the
        # real one below it.
        opened = opened_days_ago(i)

        if i % 6 == 0:
            rows.append(
                CaseAssignment(
                    case_id=case.id,
                    assignee_id=other_staff.id,
                    assigned_by_id=owner.id,
                    created_at=days_ago(opened - 1),
                )
            )

        rows.append(
            CaseAssignment(
                case_id=case.id,
                assignee_id=case.assignee_id,
                assigned_by_id=assigned_by.id,
                created_at=days_ago(opened - 2),
            )
        )

    db.add_all(rows)
    db.commit()
    return rows


def make_notes(db, cases, author):
    """Two notes per case, dated one and two days after the case opened.

    created_at has to be set explicitly. Left to the default the notes would
    be dated today, which would put today's notes on closed cases - a state
    the API itself refuses to create, since posting a note to a closed case
    returns 409.

    A case opens `opened` days ago and its first status step follows five days
    later, so notes at one and two days always fall inside the open period.
    """
    notes = []
    for i, case in enumerate(cases):
        opened = opened_days_ago(i)
        for j in range(2):
            notes.append(
                Note(
                    case_id=case.id,
                    staff_id=author.id,
                    body=NOTE_BODIES[(i + j) % len(NOTE_BODIES)],
                    created_at=days_ago(opened - 1 - j),
                )
            )
    db.add_all(notes)
    db.commit()
    return notes


def seed():
    db = localSession()
    try:
        wipe(db)

        admin, ali, sara = make_staff(db)

        ali_clients = make_clients(db, ali, ALI_CLIENT_COUNT, SOFT_DELETED_INDEXES)
        sara_clients = make_clients(
            db, sara, SARA_CLIENT_COUNT, name_offset=ALI_CLIENT_COUNT
        )

        ali_cases = make_cases(db, ali_clients, ali, sara, admin, client_count=30)
        sara_cases = make_cases(db, sara_clients, sara, ali, admin, client_count=10)

        ali_notes = make_notes(db, ali_cases, ali)
        sara_notes = make_notes(db, sara_cases, sara)

        live_ali = ALI_CLIENT_COUNT - len(SOFT_DELETED_INDEXES)
        assignments = db.query(CaseAssignment).count()
        status_rows = db.query(CaseStatusChange).count()
        total = (
            len(ACCOUNTS)
            + ALI_CLIENT_COUNT
            + SARA_CLIENT_COUNT
            + len(ali_cases)
            + len(sara_cases)
            + len(ali_notes)
            + len(sara_notes)
            + assignments
            + status_rows
        )

        print("Seeded CaseDesk demo data")
        print(f"  accounts : {len(ACCOUNTS)} (1 admin, 2 staff)")
        print(f"  clients  : {ALI_CLIENT_COUNT + SARA_CLIENT_COUNT} "
              f"({live_ali} live + {len(SOFT_DELETED_INDEXES)} soft-deleted for Ali, "
              f"{SARA_CLIENT_COUNT} for Sara)")
        print(f"  cases    : {len(ali_cases) + len(sara_cases)}")
        print(f"  notes    : {len(ali_notes) + len(sara_notes)}")
        print(f"  assigns  : {assignments}")
        print(f"  statuses : {status_rows}")
        print(f"  total    : {total} rows")
        print()
        print(f"Log in with any of these, the password is {SEED_PASSWORD} for all:")
        for entry in ACCOUNTS:
            print(f"  {entry['email']:32s} {entry['role']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
