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

The one thing it costs me is timezone-aware timestamps, which NF-06 asks for.
SQLite has no column type that stores an offset. I worked around it rather than
switching databases - see the UTC timestamps entry below. Postgres would have
given me `TIMESTAMPTZ` and no workaround at all. If this ever went live that is
the reason I would switch. Switching is not only a `DB_URL` change, though I
first wrote that it was: `database.py` passes `check_same_thread=False`, which
is a SQLite-only connect argument, and `get_current_user` compares an integer
column against the `sub` claim, which is a string - SQLite coerces that and
Postgres does not. Both would have to go.

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

1. bcrypt 72 bytes se lamba password chupchaap kaat deta hai - mana nahi
   karta. So every place a password arrives has `max_length=72`:
   `StaffRegister`, `StaffUpdate` and `PasswordChange`.

   This entry claimed that was true long before it was. `StaffRegister` had
   only `min_length=8`, so a 100-character password was accepted, bcrypt kept
   the first 72, and anyone who knew those 72 could log in with any ending at
   all. Written down as done, never written in code - which is worse than
   leaving it out of the doc, because nobody goes looking for it again.
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

### Pagination: cursors, newest first

**Decided** — `ORDER BY id DESC`, paged with `?before=<id>`, and `total` from a
separate count using the same filters.
**Rejected** — Offset paging. Ordering oldest-first.

US-17 says adding a record while someone is paging must not cause a duplicate or
a skipped row.

I got this wrong the first time. I started with `ORDER BY id` ascending and
offset, which does satisfy US-17 - new rows take the highest id and land at the
end, so the pages already visited do not move. But it also means the client you
just created is on the last page, which is a bad way to use the app.

Ordering newest-first with an offset would have broken US-17. I worked it
through with 25 rows: page 1 is ids 25-16, someone inserts id 26, and page 2 is
now 16-7 - id 16 appears twice and one row is never seen.

Cursors fix both at once. Page two asks for rows *before* the last id page one
showed, so anything created in between has a higher id and falls outside that
window entirely. Nothing shifts, because nothing is counted from the start.

The cost is that "jump to page 5" is not possible, and Previous needs the
frontend to remember the cursors it has used. Both lists only have Previous and
Next buttons, so neither costs anything in practice.

Notes were newest-first from the start, and a related problem showed up there. SQLite's `now()` only goes down to the second,
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

**Decided** — pytest, a separate `pytest_casedesk.db` file, the schema built
once by `alembic upgrade head`, tables emptied between tests, and
`app.dependency_overrides` to point the app at it.
**Rejected** — Mocking the session. Using my normal development database.

NF-03 asks for a real database. Also, most of what matters in this project *is*
the query — a fake session would just agree with whatever my code did, including
the bugs.

`dependency_overrides` was the part I did not know about. It replaces `get_db`
only, and the whole app moves to the test database without me changing a single
route.

Clearing the tables between tests means a test can check a count without
caring which tests ran before it, and the order the tests run in stops
mattering.

The first version dropped and recreated the tables for every test, with
`create_all()`. That was wrong in a way I did not see for a while: it builds
the schema from the models, so the migrations were never run by anything. A
migration could be broken, missing, or drifted from the models and all of the
tests would still pass - which is the opposite of what NF-02 asks for.

Now a session fixture runs `alembic upgrade head` once, and each test empties
the tables afterwards. The schema under test is the one the migrations
produce, and `test_migrations.py` additionally checks that the downgrades run
and that the two descriptions still agree.

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

---

### One error shape for the whole API

**Decided** — Two exception handlers in `main.py` that rewrite every failure
into `{"error": {"status", "message", "fields"}}`.
**Rejected** — Leaving FastAPI's defaults. Writing one handler instead of two.

NF-05 asks for one shape, and out of the box there are two: the errors I raise
give `{"detail": "some string"}` and Pydantic's validation errors give
`{"detail": [ ...list of objects... ]}`. The frontend had to branch on which one
it got, in five different places, which is exactly the mess the requirement is
warning about.

Two handlers rather than one because the two exceptions are unrelated classes
with different attributes - one has `.detail`, the other has `.errors()`. One
function registered for both would work, but it needs an `isinstance` check
inside, and two short handlers read better than one with a branch.

The part that caught me out: registering on FastAPI's `HTTPException` misses the
404 and 405 that Starlette raises by itself for an unknown route or a wrong
method - those kept coming back in the old shape. FastAPI's class is a subclass
of Starlette's, so registering on the parent catches both. There is a test for
each of those two cases now, because I would not have thought to check by hand.

Nothing in the routers changed. They still `raise HTTPException(404, "...")` and
the handler reshapes it on the way out.

---

### UTC timestamps on a database that cannot store them

**Decided** — A `UTCDateTime` column type that converts to UTC on the way in and
tags values as UTC on the way out, with defaults moved to Python.
**Rejected** — Moving to Postgres for `TIMESTAMPTZ`. Leaving NF-06 unmet.

I checked what SQLAlchemy actually emits for each database:

    DateTime(timezone=True) on postgresql  ->  TIMESTAMP WITH TIME ZONE
    DateTime(timezone=True) on mysql       ->  DATETIME
    DateTime(timezone=True) on sqlite      ->  DATETIME

So `timezone=True` was doing nothing at all on SQLite - it is silently ignored.
Interestingly MySQL ignores it too, so switching there would not have helped
either; only Postgres, SQL Server and Oracle really store the offset.

Rather than move the whole project to Postgres for this one line, I put the
timezone back at the edges. `process_bind_param` converts whatever it is given
to UTC before writing; `process_result_value` tags what comes back as UTC. The
application never sees a naive datetime, and the API now sends
`2026-08-27T05:20:50Z` instead of `2026-08-27T05:20:50`.

The part I nearly missed: `server_default=func.now()` runs inside SQLite, not in
Python, so those values would have skipped the conversion completely. The
defaults are now `default=utcnow` on the Python side, and a hand-written
migration drops the old server defaults so the schema and the models agree.
Alembic could not generate that one itself - it only compares server defaults
when `compare_server_default` is switched on.

What this does not do is make the database enforce anything. The bytes on disk
are still naive, and the guarantee only holds because everything goes through
SQLAlchemy. Seven tests cover it; I checked they fail if the type is removed,
because a test that cannot fail is not worth having.

---

### An assignee can see the case assigned to them

**Decided** — A case is visible to its owner and to its assignee. The assignee
can open it and add notes; nothing else.
**Rejected** — Ownership only, which is what US-15 literally says.

This is the one place I have deliberately gone against the brief, so it is worth
setting out.

US-15 says my cases are invisible to other staff. US-11 wants them filtered by
assignee "so that I can see what is on my plate". Both cannot be true at once:
if only the owner can see a case, then assigning one to a colleague hands them
work they cannot open, and the assignee filter has nothing useful to filter.

I could not find a reading of the brief where assignment means anything under
strict ownership, so I widened it by the smallest amount that makes the feature
work: the assignee can read the case and write notes on it. Editing the case,
moving its status, reassigning it and reaching the client behind it all stay
with the owner. Note deletion stays with the owner too, because US-14 is
explicit - "only notes on cases I own".

The rule lives in one function, `case_visible_to` in `security.py`, next to
`get_current_user`. Everything about who can see what is in one place rather
than spread across the route handlers.

What has not changed: someone who is neither owner nor assignee still gets a
404 everywhere, search still never crosses users, and clients are still
owner-only. There is a test for each of those, and one that checks the case
disappears again the moment it is unassigned.

---

### An admin role, which the brief says not to build

**Decided** — Two roles in a `staff.role` column. Admin sees and manages
everything and is the only one who can create staff accounts.
**Rejected** — Staying with "owns it or doesn't", which is what the brief asks
for.

The brief lists "roles or permission levels beyond owns it or doesn't" under Out
of scope. This was asked for anyway, so it is here - but I want it on the record
that it is a deliberate departure, not something I missed.

The part worth explaining is where the role is checked. There are only two
places, both in `security.py`:

`require_admin` guards the admin-only routes. It answers "may this person be
here at all", so it returns 403, not 404 - unlike a client or a case, there is
no record whose existence needs hiding.

`owned_by` is the ownership filter that every list and lookup already went
through. For an admin it returns `true()`, a SQL condition that is always
satisfied, so the filter still runs and simply excludes nothing.

That second one is why this was a small change rather than a large one. Nine
places had `staff_id == current_user.id` written out by hand. If I had put
`if admin` in all nine, the tenth endpoint someone adds would have been the one
that forgot. Replacing them with one helper means "an admin sees everything" is
written once, and any new query gets it for free.

Two smaller decisions came with it:

`/auth/register` became admin-only, so the first admin cannot come from the API.
The seed writes it directly, the same way the test fixtures do. Without that row
nobody could ever register anyone.

A case now belongs to the client's owner rather than to whoever created it. For
a staff member those are the same person, so nothing changed for them. For an
admin opening a case on someone's behalf it is what keeps the case with that
staff member instead of stranding it on the admin account.

### Assignment history in its own table, not two columns on the case

The cases list needs one line under the assignee: "you assigned" or "Sara
assigned". That alone would have been two columns on `cases` -
`assigned_by_id` and `assigned_at` - overwritten on every change.

It is a table instead, `case_assignments`, one row per assignment. The reason
is what comes next: a case page and a client page that show what happened and
when. Two columns can answer "who assigned this"; only rows can answer "who
assigned it before that". Overwriting throws away the thing the timeline is
made of, and it cannot be recovered later.

The table has no `updated_at` and no `deleted_at`. Its rows are events - they
happen once and never change - and a column that tracks edits on something
that is never edited only invites code to edit it.

`assignee_id` is nullable, and a null row means the assignee was removed.
Treating unassign as an event rather than an absence is what keeps the gap
visible in the timeline instead of making the case look untouched.

Rows are written in exactly two places, the create and the update endpoint, and
the update one only writes when the value actually changed - re-saving the same
assignee is not an event. `CaseOut` carries `last_assignment` for the list and
`CaseDetailOut` carries the full `assignments` for the case page, both loaded
with `selectinload` so the query count stays flat.

### Status history: the same shape, one table over

`case_status_changes` is `case_assignments` again - append-only rows, an event
each, written from the one endpoint that can cause them. It keeps both ends of
the move, `from_status` and `to_status`, rather than only the new one, so a row
reads on its own without walking back through the table.

Its first row per case is not a transition at all: `from_status` is null, which
means the case opened. Without it the timeline starts halfway through - a case
that never left Intake would have no history, and one that moved once would
look like it began at Active.

Two parallel tables rather than one `case_events` with a `kind` column. The
generic version would have taken less schema and more code: every read would
filter by kind and every row would carry the columns of whichever event it is
not. The two tables stay honest about their own shapes, and the merged feed the
client page needs is a union at read time, which is where merging belongs.

### Removing a staff member is a soft delete, and it can be refused

The obvious version deletes the row. It cannot be that here. Notes carry their
author, and both history tables carry who did the thing - `assigned_by_id`,
`changed_by_id`. Delete the staff row and every one of those points at nobody.
SQLite does not enforce foreign keys by default, so nothing would complain at
write time; the list would simply start returning 500s later, from a query that
looks unrelated. So `deleted_at`, the same as clients and cases.

Three refusals sit in front of it, and each one exists because of a way the app
could otherwise be left broken or unattended:

An admin cannot change their own role. The last admin demoting itself leaves an
app where nobody can promote anybody - unreachable except by editing the
database by hand. Changing *another* admin's role is fine; there is a way back
from that.

An admin cannot remove their own account, for the same reason one step further
along.

Nobody can be removed while they still own live clients or cases. Their work
would belong to no one - visible to an admin, tended by nobody. It is the rule
`/clients` already applies to a client with cases: move the work first, then
remove the account. It also means the seeded staff cannot be removed until
their clients are, which is correct rather than inconvenient.

`get_current_user` checks `deleted_at` too. A token issued before the account
was removed stays cryptographically valid until it expires, so without that
check a removed account keeps working for up to thirty minutes.

---

### Concurrent edits: a version the caller sends back

**Decided** — `PATCH /cases/{id}` takes the `version` the caller was looking
at. Stale means `409`. The column moves on by one on every successful update,
and nobody outside the router can write it.
**Rejected** — Leaving US-21 alone. Locking the row in the database.

The column, the request field and the response field existed before any of
this did, which was the worst of both: the API looked like it had optimistic
locking, and the `setattr` loop was writing whatever number arrived. Sending
`{"version": 999}` simply stored 999, and a stale update overwrote silently.
A feature that looks finished and is not is worse than one that is missing.

`data.pop("version")` is the other half. The version arrives to be *read*,
never to be written; without the pop, the field that guards the row is the one
field the caller can set to anything.

The first version of this was wrong in a way that took a threaded test to see -
see the entry below.

A database-level lock would also work and would be stricter. It also holds a
transaction open across a user's thinking time, which is exactly what
optimistic locking exists to avoid.

---

### The token travels in `Authorization`, not a header called `token`

**Decided** — `HTTPBearer` with `auto_error=False`, so the token arrives as
`Authorization: Bearer <token>`.
**Rejected** — Keeping the custom `token` header. Using `auto_error=True`.

The custom header worked. What it did not do was tell anyone else about
itself: FastAPI only puts a security scheme in the OpenAPI document when the
dependency is one it recognises, so `/docs` had no **Authorize** button, and
`token` appeared on every route as an ordinary optional parameter. The
published spec said authentication was optional everywhere, which is the
opposite of US-03, and the interactive docs could not call a single protected
route.

`auto_error=False` is the part worth pointing at. Left on, FastAPI raises its
own error for a missing header - a `403`, in its own shape. NF-05 says every
failure comes back looking the same, so the missing case has to reach my own
code and become the same `401` envelope as everything else.

`get_current_user` also changed from calling `verify_token(token)` by hand to
`Depends(verify_token)`. That is what puts it in the dependency graph, which
is what FastAPI reads when it decides a route is protected.

---

### Where a check goes: shape at the edge, state in the router

**Decided** — Anything answerable from the request alone lives on the schema
or on `Query`. Anything needing the database lives in the router.
**Rejected** — Validating in the router because that is where the `raise` was
already convenient.

I wrote several of these checks in the router first, and each time the same
four things went wrong. The error came back with an empty `fields` object, so
it broke the NF-05 shape that names the offending field. It did not appear in
`/docs`. It covered `POST` and not `PATCH`, because those are two functions.
And it needed its own `None` handling - the phone check crashed with a
`TypeError` on a client that simply had no phone.

Moved to the schema, one line does all four. `Field(min_length=1)`,
`Field(pattern=PHONE)`, `Literal[...]` and `Query(ge=1, le=100)` each produce
a 422 with the field named, show up in the OpenAPI document, apply everywhere
the schema is used, and skip `None` on their own when the field is optional.

The split is the question "does answering this need a row?". Is the body
empty, is the phone shaped like a phone, is `limit` between 1 and 100, is
`"Banana"` a status - none of those need the database. Does this case exist,
is it mine, is it closed - all of those do.

The one nuance is `null`. A field being absent and a field being `null` are
different requests, and only some columns can take the second: `email` is
nullable so `null` clears it, `name` is not so `null` is a 422. A
`field_validator` handles that, because it runs on a value that was sent and
never on a default.

---

### An assignee sees names, not email addresses

**Decided** — A second, smaller `StaffMini` shape (id and name) for the
assignee picker and for every staff block embedded in a case, note or history
row. `StaffOut`, with the email address, is admin-only.
**Rejected** — One shape everywhere.

Widening visibility to the assignee was deliberate and is set out above. What
I had not thought about is what travels with a case once it is visible. Every
`owner`, `assignee`, `author` and `changed_by` block was a full `StaffOut`, so
an assignee - who is explicitly refused the client behind the case - was still
being handed their colleagues' email addresses along the way. `GET /staff`
did the same thing for the dropdown, to everybody.

So `/staff` answers with what a dropdown needs, and `/admin/staff` answers
with what the account-management screen needs. Two routes rather than one that
changes shape depending on who is asking: a response model that varies by role
is a thing you have to read the body of the function to understand, and it
cannot be described in OpenAPI at all.

This is not the duplication that `/admin/cases` was. That one returned exactly
the same rows as `/cases` for the same caller, because `case_visible_to`
already returns `true()` for an admin - it was forty-five copied lines that
answered a question already answered. These two return different columns to
different readers.

---

### Removing a staff member counts assigned work, not just owned work

**Decided** — `DELETE /staff/{id}` refuses while the account owns clients or
cases **or** is the assignee of any live case.
**Rejected** — Unassigning their cases automatically on the way out.

The first version only counted ownership, so someone with no clients of their
own could be removed while still holding twenty cases. The rows stayed pointing
at them: the list kept showing their name, but they were gone from `/staff`, so
the case page's dropdown had no option matching the stored id and rendered
blank. The screen said "nobody", the database said otherwise.

Unassigning automatically would have been quieter and worse - it decides on
someone's behalf where the work goes. Refusing makes the person doing the
removal answer that question first, which is the same reason a client with live
cases cannot be deleted either.

---

### A closed case is read-only, not just note-proof

**Decided** — `Closed` refuses new notes, and refuses title, type and assignee
changes too. Deleting it is still allowed.
**Rejected** — Leaving edits open. Blocking the delete as well.

Only notes were blocked before, which drew the line in an odd place: you could
not write on a closed case, but you could hand it to a new person. That makes
the case look like live work to whoever it lands on.

Delete stays open on purpose. A case entered by mistake needs a way out
whatever its status, and refusing that would leave rows nobody can ever remove -
the same trap the missing delete route created for clients.

---

### Password changes invalidate existing tokens

**Decided** — `staff.token_version`, an integer that goes up on every password
change and travels inside the token. `get_current_user` compares the two.
**Rejected** — Storing sessions server-side. Leaving it alone as a known JWT
tradeoff.

A JWT is valid until it expires, and nothing in the token knows the password
behind it changed. So a stolen token kept working for its full thirty minutes
after the victim changed their password - which is the one moment they were
trying to stop exactly that.

One integer is enough. It does not turn the token into a session: there is
still no per-request lookup added, because `get_current_user` was already
loading the staff row to check `deleted_at`. Admin resets bump it too, for the
same reason.

---

### The case list needs a delete route for the client rules to work

**Decided** — `DELETE /cases/{id}`, soft, owner or admin only.
**Rejected** — Leaving cases undeletable.

`cases.deleted_at` existed from the first migration and every query filtered on
it, but nothing ever wrote to it. Combined with US-19 - a client with live cases
cannot be deleted - that meant any client who had ever had a case was permanent.
US-07 quietly stopped working the moment a case was opened.

Soft, like clients and notes, because notes and both history tables point at the
case row. Owner-only rather than assignee, matching who may already edit it.

---

### Errors from bugs use the same envelope as everything else

**Decided** — A third handler on `Exception` that returns the same
`{"error": {...}}` shape with a fixed message.
**Rejected** — Letting FastAPI's default 500 through.

Two handlers covered `HTTPException` and validation, which is every failure the
code raises deliberately. Every failure it does not - an unhandled bug - came
back in FastAPI's own shape instead. NF-05 says one shape for the whole API, and
the frontend reads `data.error.message` everywhere, so the one moment it got
nothing back was the moment something had actually broken.

The message is fixed and says nothing. What went wrong belongs in the server
log, not in a browser.

---

### A `staff_id` from a non-admin is refused, not ignored

**Decided** — `POST /clients/registration` returns `403` when a staff member
sends `staff_id` at all.
**Rejected** — Dropping the field silently and giving them their own client,
which is what it did before.

The old version read nicely - "an admin can create a client for someone else,
everyone else gets themselves, whatever they send" - and was wrong in a quiet
way. The caller asked for one thing, got `200`, and got something else. Nothing
in the response said the field had been thrown away, so a bug in a caller that
sent the wrong `staff_id` would never surface.

`403`, not `404`: there is no record whose existence needs hiding here, so the
argument that makes ownership checks `404` does not apply. The action itself is
outside what this caller may do, which is exactly what `require_admin` answers
with. `422` would be wrong too - the body is well formed, the sender is not
allowed to send it.

This changed a test. `test_a_staff_member_cannot_hand_a_client_to_someone_else`
used to assert the client came back owned by the sender; it now asserts `403`
and that nothing was created at all. Worth saying out loud, because a test that
changes with the code is the one place a silent behaviour change can hide.

---

### Token lifetime comes from `.env`

**Decided** — `TOKEN_MINUTES`, read in `config.py`, used in `create_token`.
**Rejected** — Leaving `timedelta(minutes=30)` in the code. Adding it to
`REQUIRED`.

The number was hard-coded while every other setting was in `.env`, so the one
knob most likely to differ between a demo and anything else was the one you had
to edit code to change.

Not in `REQUIRED`, unlike `SECRET_KEY` and `DB_URL`. Those have no sensible
default and the app should refuse to start without them. This one defaults to
`30`, so an existing `.env` keeps working - `os.getenv("TOKEN_MINUTES", "30")`.
The `int()` around it matters: `.env` hands back strings, and `timedelta` would
fail on one much later and less clearly.

---

### The version check had to move into the `UPDATE` itself

**Decided** — One statement: `UPDATE cases SET ..., version = version + 1
WHERE id = ? AND version = ?`, and a `409` when it touches zero rows.
**Rejected** — The first version, which read the row, compared the version in
Python, and wrote afterwards.

That first version passed all nine of its tests and still lost people's work.
The three steps - read, compare, write - sat about seventy lines apart with no
lock on the row between them, so two requests arriving together both read
version 1, both passed the check, and both wrote. Four threads against a real
server gave four `200`s, a version that went from 1 to 2 instead of 1 to 5, and
three edits gone with nothing to say they had ever existed. The people who lost
their work were shown "Saved".

The tests could not have caught it. `TestClient` finishes one request before
starting the next, so the second call always reads the version the first one
wrote, and the `409` arrives exactly as intended. A race needs overlap.
`test_concurrent_writes.py` runs a real uvicorn server, gives every request its
own session, and releases four threads off a `threading.Barrier`. Reverting the
router to the old code turns it red, which is the only reason to trust it.

Two details carry the fix. The comparison lives in `WHERE`, so the database
decides rather than Python - one `UPDATE` per row at a time means the first
arrival moves the version and the rest no longer match. And `version` is
`Case.version + 1`, built in SQL, not `current_case.version + 1` computed in
Python: the Python number is the one read before the race, which is the stale
number the whole mechanism exists to reject.

`PATCH /cases/{id}/status` got the same treatment, guarding on
`status = <what we read>` since no version is sent there. Without it two
simultaneous `Intake -> Active` calls both succeeded and wrote two history rows
for one transition.

The check is no longer opt-in. A caller that sends no `version` is still not
refused for sending a stale one - there is nothing to compare - but the guard
now uses the value just read, so two simultaneous writers still resolve to one
winner. Opt-in safety was the wrong shape: the callers most likely to omit the
field are the ones least likely to handle the damage.

---

### Front-end tests mock one function, not the network

**Decided** — Vitest and Testing Library, with `vi.mock("../api")` standing in
for the whole backend and `jsdom` for the browser.
**Rejected** — Mocking `axios`. Driving a real browser with Playwright. Running
the real API behind the tests.

Every request in the app goes through one function, `apiCall` in `src/api.js`.
That was done so the `401` redirect and the error envelope lived in one place,
and it turns out to be what makes these tests one line of setup each: there is
no `axios` call anywhere else, so there is nothing else to intercept. Had the
pages each done their own fetching, every test would have had to fake the HTTP
layer instead.

A real browser would test more and cost far more to run and keep working. The
bugs these were written for did not need one: three of them were a missing
`res.ok`, and one was asking the wrong URL.

Each test was checked by putting the bug back and watching it fail. A test that
has never been red is not yet a test — it is a file that runs. This mattered
here, because all four of these were written after the fix rather than before
it, so nothing else proves they point at the right thing.

Queries use `getByLabelText`, which only matches when a label is tied to its
input with `htmlFor`. That was added earlier for accessibility; making the tests
depend on it means it cannot quietly rot.

---

### Vite pinned to 8.1.5

**Decided** — `vite@8.1.5`, not the newer `8.2.2`.
**Rejected** — Staying on 8.2.2 and skipping front-end tests. Patching
`node_modules`.

8.2.2 ships a broken bundle: the `vite:oxc` plugin calls
`zxctransformWithOxc`, and the only function in the file is
`transformWithOxc`. The name is corrupted at the call site, so any transform
through that path throws `ReferenceError`.

`npm run dev` and `npm run build` never hit it, which is why nothing looked
wrong. Vitest does, on every file it loads, so the whole suite failed to start
before a single test ran. 8.1.5 has the same call spelled correctly.

Worth writing down because it looks like a version pinned for no reason, and
the next person to bump it will land straight back on the same error.

