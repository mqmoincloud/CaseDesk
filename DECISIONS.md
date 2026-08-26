# Decisions

This is my first real Python project, so I wrote these down as I went. These are
the choices where I had to stop and think, and where someone else could easily
have picked the other option.

---

### Database: SQLite

**Decided** — SQLite (a single local file), used through SQLAlchemy.
**Rejected** — PostgreSQL in Docker.

The brief says this only runs locally, and SQLite needs nothing installed or
started. That made the "clone it and run it" requirement much easier for me.

One problem I want to be honest about: SQLite has no timezone-aware column type.
So NF-06 is only half done. I store everything in UTC, but the timezone part is
dropped when it saves and comes back without it. Postgres has a proper
`TIMESTAMPTZ` type and would have handled this by itself. If this ever went
live, that would be the reason to switch. Switching is just a `DB_URL` change
and a driver, since SQLAlchemy handles the rest.

---

### ORM: SQLAlchemy

**Decided** — SQLAlchemy with declarative models.
**Rejected** — Writing raw SQL. SQLModel.

Every single query in this app has to filter by the logged-in user. With an ORM
I write that filter the same way everywhere. With raw SQL I would be copying a
WHERE clause into every query and would definitely forget one somewhere.

I looked at SQLModel because it is less code, but it makes one class do both the
table and the API shape. I need those separate here — the `Staff` table has a
`password_hash` column and the API response must not have that field at all.

---

### Migrations: Alembic

**Decided** — Alembic, with a migration file for each schema change.
**Rejected** — `Base.metadata.create_all()`.

NF-02 says drop-and-recreate is not allowed. I did have `create_all()` in
`main.py` while I was still building the models, and I removed it once Alembic
was working — keeping both would mean two things trying to create the same
tables.

I also tested `upgrade head` → `downgrade base` → `upgrade head`. It runs clean,
so the downgrade actually works and is not just sitting there unused.

---

### Batch mode in Alembic

**Decided** — `render_as_batch=True` in `migrations/env.py`.
**Rejected** — Leaving it off.

SQLite cannot drop or change a column with `ALTER TABLE`. Without this setting
my first migration would have worked fine and the second one would have failed —
which is a bad time to find out. Batch mode makes Alembic build a new table,
copy the data over, and drop the old one.

---

### Auth: JWT token

**Decided** — A signed JWT with the staff id in `sub` and a 30 minute expiry.
**Rejected** — Sessions stored on the server. A signed cookie.

US-02 wants something that identifies the user, expires, and cannot be edited by
the client. A JWT does all three and I do not have to store anything.

A cookie would have meant learning CSRF protection too, which this app does not
need.

I only put the staff id in the token. At first I had the email in there as well,
until I realised a JWT is signed but **not encrypted** — anyone can paste it into
jwt.io and read it. So there is no reason to put anything extra in.

---

### Password hashing: bcrypt

**Decided** — bcrypt through passlib, with `bcrypt==4.0.1` pinned.
**Rejected** — argon2.

The brief allows either one. Two things went wrong along the way and both are
now handled in code:

1. bcrypt refuses passwords longer than 72 bytes. So `StaffRegister.password`
   has `max_length=72` and a long password gets a proper 422 instead of a 500.
2. passlib 1.7.4 crashes with bcrypt 4.1 and newer, because it looks for an
   attribute that got removed. That is why the version is pinned in
   `requirements.txt`, with a comment explaining it.

argon2 would have avoided both of these. If that pin ever becomes a problem,
that is the way out.

---

### How ownership is enforced

**Decided** — Every query starts with `staff_id == current_user.id` and
`deleted_at IS NULL`. If nothing comes back, return 404.
**Rejected** — Fetching the row first, then checking who owns it and returning
403 if it is someone else's.

This is the one I understand best now. A 403 tells the caller that the record
exists, which is exactly the leak US-15 talks about. So it has to be 404 either
way.

And once it is 404 either way, checking afterwards has no benefit. It is just an
`if` that I could forget to write on the next endpoint I add. As a filter I
cannot forget it, because without it the query returns rows that were never mine
to show.

I also put `staff_id` on the `Case` table even though it could be reached
through the client. That way the filter is the same one column everywhere,
instead of a join.

---

### Soft delete: a timestamp, not a boolean

**Decided** — `deleted_at`, where NULL means the row is live.
**Rejected** — An `is_deleted` True/False column.

US-07 asks for a timestamp anyway, and it is more useful — it tells me *when*,
not just *whether*.

The downside is that nothing enforces it. I have to remember `deleted_at IS NULL`
in every query myself. It caught me out once: a deleted note was still showing on
the case detail page, because relationships load soft-deleted rows too. I had to
put the condition inside the relationship with `primaryjoin` to fix it.

---

### Deleting a client who has cases: block it

**Decided** — Return 409 if the client still has any live case.
**Rejected** — Deleting their cases along with them.

Cascading is friendlier and it is one click. But it is also one click away from
wiping a client's whole history, and I have no undelete endpoint to get it back.

Blocking makes the user handle the cases first. Slower, but at least it is
honest about what is being thrown away.

The count only looks at live cases, so if all the cases are already deleted the
client can still be removed.

---

### Pagination: offset, ordered by id going up

**Decided** — `ORDER BY id` ascending with `offset`/`limit`, and `total` from a
separate count using the same filters.
**Rejected** — Cursor pagination. Ordering newest-first.

US-17 says adding a record while someone is paging must not cause a duplicate or
a skipped row.

Ordering newest-first breaks that. A new row goes to the top, everything shifts
down one place, and page 2 shows something the user already saw on page 1.
Ordering by id going up puts new rows at the end instead, so the pages already
visited do not move. That gives me what US-17 asks for without cursors, which I
would have found much harder.

The trade-off is that the newest client shows up last. For a list you search
anyway, I can live with that.

Notes are the opposite — they have to be newest-first — and the same problem
showed up there in a smaller way. SQLite's `now()` only goes down to the second,
so two notes added in the same second had the exact same timestamp and came back
in the wrong order. Adding `Note.id.desc()` as a second sort key fixed it.

A test found that one. Clicking through by hand never would have, because you
cannot add two notes in the same second manually.

---

### Case status gets its own endpoint

**Decided** — `PATCH /cases/{id}/status`, with the allowed moves in a dictionary,
and `status` taken out of `CaseUpdate` completely.
**Rejected** — Handling status inside the normal PATCH.

US-18 has to work for any caller, not just my own UI. If `status` had stayed in
`CaseUpdate`, my `setattr` loop would just write whatever was sent, and anyone
could jump straight from Intake to Closed in one request. Hiding the buttons in
the frontend would not have mattered at all.

I put the transitions in a dictionary instead of a chain of `if`s. That way the
whole lifecycle is visible in four lines and the actual check is one line.

One thing I know is not quite right: sending a nonsense status like `"Banana"`
gives a 409, not a 422. It just is not in the allowed list, so it falls through
the same check. Using an Enum in the schema would make it a proper 422 and would
also give Swagger a dropdown. That is the next thing I would fix.

---

### Making list queries fast

**Decided** — `selectinload` on `Case.client` and `Case.assignee` in the list
endpoint.
**Rejected** — Leaving it lazy. Doing the join myself and building the rows by
hand.

US-11 needs the client name and assignee name in the list. Reading those names
is what makes SQLAlchemy go and fetch them, so without eager loading a 50-row
page runs about 100 queries. I would never have noticed with 3 test rows.

`selectinload` runs one extra query per relationship instead of one per row. I
measured it: 4 queries for a 50-row page.

The test for this counts the actual SQL statements and checks that a 10-row page
and a 50-row page cost the **same** number. I did it that way instead of
checking for an exact number, because the number could change for a good reason
later, but it growing with the page size never would be.

---

### Tests: pytest against a real database

**Decided** — pytest, a separate `pytest_casedesk.db` file, tables created and
dropped for each test, and `app.dependency_overrides` to point the app at it.
**Rejected** — Mocking the session. Using my normal development database.

NF-03 asks for a real database. Also, most of what matters in this project *is*
the query — a fake session would just agree with whatever my code did, including
the bugs.

`dependency_overrides` was the part I did not know about. It replaces `get_db`
only, and the whole app moves to the test database without me changing a single
route.

Dropping the tables between tests means a test can check a count without caring
which tests ran before it. It makes the suite a few seconds slower and I think
that is worth it.

---

### Seeding only when the database is empty

**Decided** — `run.py` seeds a fresh database, skips if there is already data,
and has a `--reseed` flag to force it.
**Rejected** — Seeding every time the server starts.

The seed script deletes everything before it inserts, which is what makes it
repeatable. But it also means that if it ran on every start, everything I had
added by hand would disappear every time I restarted.

NF-01 is still satisfied: a fresh clone has no staff, so the one command does
seed it.

The seed uses no random values at all, so the demo data comes out identical on
every machine and tests can rely on it.
