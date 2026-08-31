# CaseDesk

A small internal web app for a law firm. Staff record **clients**, open **cases**
against them, and log **notes** on each case. Everything runs locally.

Built with FastAPI, SQLAlchemy and SQLite on the backend, React (Vite) on the
front. The reasoning behind each of those choices is in [DECISIONS.md](DECISIONS.md).

---

## Running it

You need Python 3.11 or newer.

```bash
cd Backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env           # Windows: copy .env.example .env
```

Open `.env` and set `SECRET_KEY` to something long and random:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then, from `Backend/`:

```bash
python run.py
```

That one command applies the migrations, seeds demo data if the database is
empty, and starts the server on <http://127.0.0.1:8000>.

Interactive API docs: <http://127.0.0.1:8000/docs>

### Demo accounts

The seed creates an admin and two staff members, so both the ownership rules
and the admin role are visible straight away.

| Email | Role | Password |
|---|---|---|
| `admin@casedesk.example.com` | admin | `password123` |
| `ali@casedesk.example.com` | staff | `password123` |
| `sara@casedesk.example.com` | staff | `password123` |

Ali has 65 clients (two of them soft-deleted) and 60 cases; Sara has 20 clients
and 19 cases. The seed spreads cases over 30 and 10 clients respectively, and
gives each of those clients one, two or three cases — so some clients have
several and some have none, which is what makes the delete rules visible.
Neither staff member can see the other's. The admin sees everything and owns
nothing.

The admin has to come from the seed: `/auth/register` is admin-only, so without
that first row nobody could ever create an account.

### Starting over

`run.py` leaves existing data alone. To wipe it and rebuild the demo data:

```bash
python run.py --reseed
```

---

## Tests

From `Backend/`, with the virtualenv you created above activated:

```bash
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pytest
```

236 tests, one file per epic. They run against a real SQLite database
(`pytest_casedesk.db`) — nothing is mocked, so a broken query fails a test
instead of slipping past a fake session. Your development database is
untouched.

The schema is built by running `alembic upgrade head`, not by `create_all()`.
That is the point of NF-02: a broken or missing migration fails the whole
suite rather than passing against a schema the migrations never produced.
Tables are emptied between tests, so a count assertion in one test can't be
thrown off by rows another test left behind.

| File | Covers |
|---|---|
| `test_auth.py` | Register, login, protected routes |
| `test_clients.py` | Client CRUD, search |
| `test_cases.py` | Case CRUD, filters |
| `test_notes.py` | Adding and deleting notes |
| `test_isolation.py` | One user cannot reach another's records |
| `test_assignee_access.py` | What an assignee may and may not do |
| `test_admin.py` | The admin role, and that staff cannot reach it |
| `test_profile.py` | Reading and changing your own account |
| `test_pagination.py` | Cursor paging stays correct across 65 records |
| `test_status_rules.py` | Case lifecycle, deleting a client with cases |
| `test_query_count.py` | List endpoints do not issue one query per row |
| `test_error_contract.py` | Every error comes back in the same shape |
| `test_timestamps.py` | Timestamps are UTC and timezone-aware |
| `test_concurrent_edits.py` | A stale update is refused, not silently applied |
| `test_migrations.py` | Migrations run both ways, and match the models |
| `test_concurrent_writes.py` | Simultaneous saves: one wins, the rest get `409` |
| `test_assignment_history.py` | Who assigned what, and when |
| `test_status_history.py` | The status timeline |
| `test_case_filters.py` | Status, assignee and client filters combine |
| `test_staff_admin.py` | Creating, editing and removing accounts |

`test_concurrent_writes.py` is the other odd one: it starts a real uvicorn
server on a spare port and releases four threads off a `threading.Barrier`.
Everything else uses `TestClient`, which finishes one request before beginning
the next — fine for every other rule, useless for a race.

`test_query_count.py` is the odd one out: it hooks SQLAlchemy's
`before_cursor_execute` and counts the statements a page actually issues, then
asserts that a 10-row page and a 50-row page cost the same.

### Front end

```bash
cd Frontend
npm test          # once
npm run test:watch
```

14 tests over four screens, with Vitest and Testing Library. Nothing here talks
to a server: `jsdom` stands in for the browser and `vi.mock("../api")` stands in
for the backend. That second one is one line per file only because every request
in the app goes through the single `apiCall` function in `src/api.js` — there is
no `axios` call anywhere else to intercept.

The assertions themselves take about a second, and a warm `npm test` finishes
in under three. The first run after a fresh clone is the slow one — around
forty-five seconds while Vite pre-bundles its dependencies into
`node_modules/.vite`. Every run after that reuses the cache.

Each of them was written against a bug that had actually shipped, and each was
checked by putting the bug back and watching the test go red:

| Screen | What it holds down |
|---|---|
| `NewClient` | The owner picker asks `/admin/staff`, the endpoint that sends `role`. Asking `/staff` returns id and name only, so the filter dropped every option and the dropdown was always empty. |
| `StaffList` | A `500`, and an unreachable server, produce a message instead of a blank page — `res.data` is the error envelope, and `.map` on it throws away the whole tree. |
| `EditClient` | Same check on the load path, plus that it does not sit on "Loading..." for ever when the request never lands. |
| `EditCase` | A closed case shows a message rather than an editable form, and a save carries the `version` the page was looking at. |

Queries go through `getByLabelText`, which only finds a field when its label is
tied to it with `htmlFor`. That makes the accessibility fix from earlier
load-bearing rather than decorative: break the pairing and these tests fail.

---

## API

Every route below needs an `Authorization: Bearer <token>` header — the token
comes from `/auth/login`. It is a declared security scheme, so the **Authorize**
button in `/docs` works and the interactive docs can call protected routes.

```
POST   /auth/register             admin only - staff cannot self-register
POST   /auth/login
GET    /me                        who the token belongs to, and their role
PATCH  /me                        change your own name
POST   /me/password               change your own password
GET    /staff                      id and name only - the assignee picker
GET    /admin/staff                admin only - the full list, with emails
PATCH  /staff/{id}                 admin only
DELETE /staff/{id}                 admin only - soft delete

POST   /clients/registration       admin may pass staff_id to hand it to someone
GET    /clients                    ?search= &before= &limit=
GET    /clients/{id}
PATCH  /clients/{id}
DELETE /clients/{id}

POST   /cases/registration
GET    /cases                      ?status= &assignee= &client_id= &search= &before= &limit=
GET    /cases/{id}                 includes the client and its notes
PATCH  /cases/{id}                 send `version` to be told about a clash
PATCH  /cases/{id}/status
DELETE /cases/{id}                 owner or admin - soft delete

POST   /cases/{id}/notes
DELETE /notes/{id}
```

### Status codes

Every error - including the ones FastAPI and Starlette raise on their own -
comes back in the same shape:

```json
{ "error": { "status": 404, "message": "Client not found", "fields": {} } }
```

`fields` is filled in only for validation errors, where it maps a field name to
what was wrong with it:

```json
{ "error": { "status": 422, "message": "Validation failed",
             "fields": { "password": "String should have at least 8 characters" } } }
```

| Code | Meaning |
|---|---|
| `401` | Not authenticated |
| `404` | Not found, or not yours |
| `409` | Duplicate, or a disallowed state change |
| `422` | Validation error |

`404` covers both "does not exist" and "belongs to someone else" on purpose. A
`403` would confirm the record exists, which is itself a leak.

### Paging

Lists come back newest-first and are paged by cursor, not by page number:

```
GET /clients?limit=10                 first page
GET /clients?limit=10&before=57       the next ten, older than id 57
```

The response carries `next_cursor`, which is the id to pass as `before` for the
following page. `total` is the size of the filtered set, and `has_next` says
whether another page exists.

Cursors rather than `?page=2` because a record created mid-walk takes a higher
id and falls outside the window a later page asks for. With an offset it would
push every row down one place and the next page would repeat one (US-17).

### Concurrent edits

`PATCH /cases/{id}` accepts the `version` the caller was looking at. If the row
has moved on since, somebody else saved in between and writing now would wipe
their change, so the API answers `409` instead.

```
GET   /cases/7                     -> { ..., "version": 3 }
PATCH /cases/7  {"title": "New", "version": 3}   -> 200, version is now 4
PATCH /cases/7  {"title": "Mine", "version": 3}  -> 409
```

`version` cannot be written — sending it is how the check is passed, not a way
to set it.

The comparison happens inside the `UPDATE`, not in Python before it:

```sql
UPDATE cases SET title = ?, version = version + 1
 WHERE id = ? AND version = ?
```

If it touches zero rows, somebody got there first and the answer is `409`.
Doing it the other way — read, compare, then write — passes every sequential
test and still loses work when two saves overlap, because both read the same
version before either writes. `test_concurrent_writes.py` runs a real server
and four threads to hold that down.

A caller that sends no `version` is not refused, but the guard still uses the
value just read, so simultaneous writers resolve to one winner either way.

`PATCH /cases/{id}/status` moves the version on as well. Without that a status
change would be invisible to the check: somebody could move the case to
`Active` while your page was open, and your stale `version` would still match.

### Roles

Two roles, kept in `staff.role`.

**Staff** see and manage only their own clients and cases - the whole of the
rest of this README describes their view.

**Admin** can see and manage everything, and is the only one who can create
staff accounts. An admin can also create a client on a staff member's behalf by
passing `staff_id`, and open a case on it; the case belongs to the client's
owner, not to whoever created it.

The role is checked in two places, both in `src/security.py`: `require_admin`
guards admin-only routes, and `owned_by` is the ownership filter every list and
lookup goes through - it simply excludes nothing when the caller is an admin.

In the UI an admin gets a **Staff** page for creating accounts, and an extra
"Belongs to" picker on the new-client form. The role comes from `GET /me` on
every page load - it is never kept in `localStorage`, because anything stored in
the browser can be edited by whoever is sitting at it. Even so, both are only
hiding and showing: the API refuses a staff member either way.

The brief puts roles out of scope. See [DECISIONS.md](DECISIONS.md).

### Your own account

Everyone, admin or staff, gets a **Profile** page from the sidebar. It shows the
email, role and join date, and lets you change your name and your password.

None of the three routes takes an id - they act on whoever the token belongs to,
so there is no way to aim them at another account. Changing a password requires
the current one, so an unlocked screen cannot be used to take the account over.

Email is not editable there. It is the login identifier, and a typo would lock
you out; an admin can sort it out if it really needs changing.

### Who can see a case

A case is visible to the staff member who owns it and to whoever it is
assigned to. The assignee can open it and add notes. Editing it, moving its
status, reassigning it and opening the client behind it stay with the owner.
Clients are owner-only throughout. See [DECISIONS.md](DECISIONS.md) for why
this differs from a strict reading of the brief.

The case detail screen follows the same split. `CaseOut` carries an `owner`, so
the page can tell "this is mine" from "I am only assigned to it" and leave out
the controls that would only earn a 404 - the assignee dropdown, the status
button and the delete link on each note. The note box stays, because writing
notes is the part an assignee is meant to do.

### Case lifecycle

```
Intake  ->  Active  ->  Settled  ->  Closed
```

One step at a time. Skipping one returns `409`, and `Closed` is the end — a
closed case cannot be reopened. This is enforced in the API, not just hidden in
the UI, so it holds for any caller.

A closed case is read-only: it cannot take new notes, and its title, type and
assignee cannot be changed either (`409` for all of them). It can still be
deleted, because a case entered by mistake needs a way out whatever its status.

---

## Layout

```
Backend/
├─ run.py                  one command: migrate, seed, serve
├─ requirements.txt
├─ .env.example
├─ alembic.ini
├─ migrations/             versioned schema changes
├─ scripts/seed.py         demo data
├─ src/
│  ├─ main.py              app, CORS, routers
│  ├─ config.py            reads .env
│  ├─ database.py          engine, session, get_db
│  ├─ security.py          hashing, JWT, get_current_user
│  ├─ models/              SQLAlchemy tables
│  ├─ schemas/             Pydantic request/response shapes
│  └─ routers/             auth, clients, cases, notes
└─ tests/

Frontend/                  Vite + React, Vitest for the screen tests
```

Models and schemas are deliberately separate. `Staff` has a `password_hash`
column; `StaffOut` does not have the field at all, so the hash cannot leak into
a response even by accident.

---

## Known gaps

- **SQLite stores timestamps without an offset.** The `UTCDateTime` type in
  `src/database.py` converts to UTC on the way in and tags values as UTC on the
  way out, so everything the app and the API see is timezone-aware. The bytes on
  disk are still naive, though - the guarantee lives in the application, not in
  the database. Postgres would enforce it with `TIMESTAMPTZ`.

- **A case list loads the full history of every case on the page.** `/cases`
  uses `selectinload` for the assignment and status tables so it can show the
  most recent of each. The query count stays flat (that is what US-20 asks for,
  and what `test_query_count.py` checks), but a case with fifty events fetches
  all fifty rows to display one. A `max(id)` subquery per page would fix it;
  at this size it has not been worth the extra complexity.

- **There is no refresh token and no server-side logout.** The lifetime comes
  from `TOKEN_MINUTES` in `.env` (default 30). Changing a password invalidates
  every existing token, because `staff.token_version` moves on and the token
  carries the version it was signed with — but logging out only clears the
  browser's copy. The token itself stays valid until it expires, so there is no
  way to end one device's session.

- **Nothing rate-limits `/auth/login`.** Wrong passwords cost the attacker only
  the time bcrypt takes; no account ever locks.

- **The database enforces none of the value rules.** `status`, `role` and
  `case_type` are plain `String` columns with no `CHECK` constraint, so the
  rules live entirely in the API. A row edited by hand can hold anything, and
  the app will read it back and display it.
