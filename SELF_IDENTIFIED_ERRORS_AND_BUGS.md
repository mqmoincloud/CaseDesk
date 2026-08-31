# Self-identified errors and bugs

A review of my own code, written before the walkthrough rather than after it.

Everything marked **CONFIRMED** was reproduced by running it — the output is
quoted underneath. Everything else is read from the code and named honestly as
unverified.

**All of these are now fixed**, along with a second round found afterwards by
running the code rather than reading it (listed at the bottom). Each fix has a
test, and the suite is at 240.

The file stays because the point of it was never the list - it was being able
to say why each one happened. The write-ups below are unchanged from when the
bug was live, so they still read as "here is what I got wrong", which is the
useful part in a walkthrough.

**Not covered here:** the repository hygiene work (commit granularity, untracked
files) which I am handling separately, and the two deliberate departures from
the brief — the admin role and the assignment/status history — which were asked
for and are already recorded in `DECISIONS.md`.

---

## Summary

| #   |                        Issue                           | Severity | Status    |
|---  |--------------------------------------------------------|----------|-----------|

| A.1 | `?limit=0` / `?limit=-1` crashes the server with a 500 | Critical | Fixed |
| A.2 | `limit` has no upper bound — `?limit=100000` is accepted | High | Fixed |
| B.1 | Phone is not validated at all (US-04 acceptance criterion) | High | Fixed |
| B.2 | `version` is client-writable and enforces nothing (US-21) | High | Fixed |
| B.3 | Empty note body / empty case title are accepted | Medium | Fixed |
| B.4 | `%` and `_` are not escaped in search | Medium | Fixed |
| C.1 | A soft-deleted staff member can still be assigned a case | High | Fixed |
| C.2 | An admin can create a client for a soft-deleted staff member | High | Fixed |
| C.3 | `PATCH /clients/{id}` with `"name": null` returns 500 | High | Fixed |
| C.4 | Unknown status value would raise `KeyError` → 500 | Medium | Fixed |
| C.5 | A non-admin's `staff_id` is silently ignored instead of rejected | Low | Fixed |
| C.6 | A `Closed` case can still be edited and take new notes | Low | Fixed |
| D.1 | `/admin/cases` is a copy-paste of `/cases` with identical output | High | Fixed |
| D.2 | Leftover junk: stray comment, commented import, duplicate imports | Low | Fixed |
| D.3 | `npm run lint` fails with 3 errors | Medium | Fixed |
| E.1 | Tests use `create_all()`, so migrations are never exercised | High | Fixed |
| E.2 | Suite takes 3.5 minutes; `DECISIONS.md` says "a few seconds" | Low | Fixed |
| E.3 | No test for `upgrade → downgrade → upgrade` | Low | Fixed |
| E.4 | `test_query_count.py` sends a `page=1` param that does not exist | Low | Fixed |
| F.1 | OpenAPI has no security scheme — `/docs` cannot authenticate | High | Fixed |
| F.2 | Bare `except:` in `verify_token` | Medium | Fixed |
| F.3 | Config has no validation — a missing `.env` fails cryptically | Medium | Fixed |
| F.4 | `DECISIONS.md` claim about switching databases is wrong | Medium | Fixed |
| F.5 | A nonsense status returns 409 instead of 422 | Low | Fixed |
| F.6 | `change_password` returns 403, which is not in my error contract | Low | Fixed |
| F.7 | A missing token reports "Invalid or expired token" | Low | Fixed |
| F.8 | `GET /staff` exposes every colleague's email to every user | Low | Fixed |
| F.9 | An assignee is shown the client name and the owner's email | Medium | Fixed |
| F.10 | Non-RESTful route names (`/clients/registration`) | Low | Fixed |
| G.1 | `Clients.jsx` does not URL-encode the search term; `Cases.jsx` does | Medium | Fixed |
| G.2 | `validateStatus: () => true` plus partial status checks → blank page | High | Fixed |
| G.3 | Hardcoded `limit=100` silently truncates two lists | Medium | Fixed |
| G.4 | Delete confirmation exists on two screens out of four | Medium | Fixed |
| G.5 | The client link in the case list always 404s for an assignee | Medium | Fixed |
| G.6 | `window.location.reload()` used to refresh the sidebar | Low | Fixed |
| G.7 | `setRefresh(refresh + 1)` in one file, `setRefresh(n => n + 1)` in two | Low | Fixed |
| G.8 | Frontend API base URL is hardcoded | Low | Fixed |
| G.9 | No global 401 handling — every page repeats it, some omit it | Medium | Fixed |
| H | Six documentation claims that no longer match the code | Medium | Fixed |
| I | Mixed-language comments; two are notes-to-self, not comments | Low | Fixed |

---

## A. The server can be crashed by a query parameter

### A.1 `?limit=0` and `?limit=-1` return a 500 — CONFIRMED

```
GET /clients?limit=-1  ->  IndexError: list index out of range
GET /clients?limit=0   ->  IndexError: list index out of range
GET /cases?limit=-1    ->  IndexError: list index out of range
```

`src/routers/clients.py:66-70`:

```python
rows = all_clients.order_by(Client.id.desc()).limit(limit + 1).all()

has_next = len(rows) > limit        # limit=0 -> 1 > 0 -> True
items = rows[:limit]                # rows[:0] -> []
next_cursor = items[-1].id if has_next else None   # [][-1] -> IndexError
```

With `limit=0` the query still asks for one row, so `has_next` comes back True
while `items` is empty, and `items[-1]` then raises. It fires whenever the table
holds at least one row, which is always.

`limit` is not validated anywhere — no minimum, no maximum, no cap. The same
block is duplicated in `src/routers/cases.py:138-142`, so the bug exists in
three list endpoints.

This breaks three requirements at once: NF-05 (a 500 is not in my error
contract), US-17 (paging is meant to be trustworthy) and US-20.

**Fix:** `limit: int = Query(10, ge=1, le=100)` and
`before: int | None = Query(None, ge=1)`. One line each, three endpoints.

### A.2 `limit` has no upper bound — CONFIRMED

```
GET /clients?limit=100000  ->  200, returns every row
```

Any caller can pull the whole table in one request, which is the thing US-20
asks me to prevent. Same fix as A.1.

---

## B. Acceptance criteria I did not meet

### B.1 Phone is not validated — CONFIRMED

US-04: *"Name is required. **Phone and email are format-validated** when
present."*

```
POST /clients/registration  {"name":"P","phone":"not-a-phone-!!!@@@"}  ->  200
```

Email is covered by `EmailStr`. Phone is `phone: str | None = None` in
`src/schemas/client.py:7` — no pattern, no length, nothing. I validated one half
of the criterion and moved on.

**Fix:** a `pattern` constraint on `ClientRegister.phone` and
`ClientUpdate.phone`, plus a test for the 422.

### B.2 `version` is client-writable and enforces nothing — CONFIRMED

```
PATCH /cases/1  {"title":"x","version":999}  ->  200, stored version = 999
PATCH twice with the same stale version=1    ->  200 (should be 409)
```

The column is in `src/models/case.py:19`, the field is in `CaseUpdate`
(`src/schemas/case.py:62`), and it is returned in `CaseOut`. The route's
`setattr` loop writes whatever arrives and never compares or increments it.

This is worse than not attempting US-21. The column, the request field and the
response field all say the feature exists, so a caller would reasonably trust
it. What actually happens is that a client can set `version` to any number it
likes, and a stale update silently overwrites.

**Fix — either finish it:**

```python
if new_info.version is not None and new_info.version != current_case.version:
    raise HTTPException(409, "This case was changed by someone else")
...
current_case.version += 1
```

(and drop `version` from the `setattr` loop)

**or remove it** from the model, the schema and the response, and say in
`DECISIONS.md` that the stretch was not attempted. Half-built is the one option
I should not ship.

### B.3 Empty values are accepted — CONFIRMED

```
POST /cases/1/notes        {"body":""}                   ->  200
POST /cases/registration   {"title":"","case_type":""}   ->  200
```

`NoteRegister.body`, `CaseRegister.title` and `case_type` have no `min_length`.
Nothing in the project has a `max_length` except the password, so there is also
no upper bound on any text field.

**Fix:** `Field(min_length=1, max_length=...)` across the write schemas.

### B.4 `%` and `_` are not escaped in search — CONFIRMED

```
GET /clients?search=%25  ->  total: 1 of 1  (every row matches)
```

`src/routers/clients.py:52` builds `f"%{search.lower()}%"` and passes it
straight to `LIKE`. A user typing `%` matches everything and a user typing `_`
matches any single character. US-08 asks for partial-string matching, not
wildcard passthrough.

**Fix:** escape `%`, `_` and `\` in the term, then `.like(term, escape="\\")`.

---

## C. Data integrity holes

### C.1 A soft-deleted staff member can still be assigned a case — CONFIRMED

```
DELETE /staff/2                       ->  200
PATCH  /cases/1 {"assignee_id": 2}    ->  200
```

The assignee lookups at `src/routers/cases.py:33-35` and `:211` filter on
`Staff.id` only — no `deleted_at.is_(None)`. `GET /staff` does exclude removed
accounts, so the result is a case showing an assignee who is not in the assignee
dropdown.

### C.2 An admin can create a client for a soft-deleted staff member — CONFIRMED

```
DELETE /staff/2                                          ->  200
POST /clients/registration {"name":"Ghost","staff_id":2} ->  200
```

Same missing filter, at `src/routers/clients.py:21`.

This one contradicts my own reasoning. `DECISIONS.md` explains that removal is
refused while someone still owns live work, because *"their work would belong to
no one — visible to an admin, tended by nobody."* That rule is enforced on the
way out and then bypassed on the way in: after the account is removed, new work
can still be handed to it.

**Fix for C.1 and C.2:** add `Staff.deleted_at.is_(None)` to all three lookups.

### C.3 `PATCH /clients/{id}` with `"name": null` returns 500 — CONFIRMED

```
sqlite3.IntegrityError: NOT NULL constraint failed: clients.name
```

`ClientUpdate.name` is `str | None = None`, so `null` passes validation, the
`setattr` loop writes `None`, and the database rejects it as an unhandled 500 —
outside my own NF-05 contract. The same shape of bug applies to
`CaseUpdate.title` and `CaseUpdate.case_type`.

The optional-field types are doing two jobs at once: "may be omitted" and "may
be null". Only the first is wanted.

**Fix:** keep the fields optional but non-nullable, or reject explicit nulls
before the `setattr` loop.

### C.4 An unexpected status value would raise `KeyError` — unverified

`src/routers/cases.py:254` — `ALLOWED_TRANSITIONS[current_case.status]` is a
bare dictionary lookup. Every path that writes `status` today goes through the
transition check, so I could not reach it from the API; a row written by hand or
by a future code path would produce a 500 rather than a handled error.

**Fix:** `ALLOWED_TRANSITIONS.get(current_case.status, [])`.

### C.5 A non-admin's `staff_id` is silently ignored — CONFIRMED

```
POST /clients/registration {"name":"X","staff_id":<someone else>}  as staff
  ->  200, the client is created under the caller instead
```

The behaviour is safe — ownership is not transferable by a staff member — but it
is silent. The caller is told the request succeeded as sent when part of it was
discarded. A 422 would be honest; at minimum it belongs in the README.

### C.6 A `Closed` case can still be edited and take new notes — CONFIRMED

```
PATCH /cases/1 {"title":"edited after close"}  ->  200
POST  /cases/1/notes {"body":"after close"}    ->  200
```

The brief only says the *status* is terminal, and that part is enforced. Whether
a closed case should also freeze its title, type, assignee and notes is a
judgement call I never actually made — the current behaviour is a default, not a
decision. Either way it belongs in `DECISIONS.md`.

---

## D. Duplicate and dead code

### D.1 `/admin/cases` is a copy of `/cases` and returns identical output — CONFIRMED

```
GET /cases        as admin  ->  total: 0
GET /admin/cases  as admin  ->  total: 0
responses identical: True
```

`src/routers/cases.py:149-194` is a 45-line copy-paste of the endpoint above it.
The only difference is `require_admin` and dropping `case_visible_to()` — but
`case_visible_to()` already returns `true()` for an admin, so `/cases` shows an
admin everything anyway. The endpoint adds nothing.

This is the finding I am least happy about, because `DECISIONS.md` argues
against exactly this:

> *"Nine places had `staff_id == current_user.id` written out by hand. If I had
> put `if admin` in all nine, the tenth endpoint someone adds would have been
> the one that forgot."*

I made the case for a single shared filter and then wrote a duplicate endpoint
anyway. It should be deleted, and the frontend should call `/cases`.

### D.2 Leftover junk — CONFIRMED

| Location | What |
|---|---|
| `src/routers/cases.py:148` | `# Qaisar Moin` — my name left in the middle of the router |
| `Frontend/src/App.jsx:5` | `// import CaseDetail from "./pages/CaseDetail";` directly above the real import |
| `src/routers/auth.py:7` and `:9` | the same three functions imported twice |
| `alembic.ini:89` | still the generated placeholder `driver://user:pass@localhost/dbname` |
| `security.py`, `clients.py`, `cases.py`, `notes.py`, `schemas/case.py` | 18-30 trailing blank lines each |
| `src/models/client.py:17` | `Client.cases` has no `deleted_at` condition, unlike `Case.notes`; currently unused, so not a live bug, but inconsistent |

### D.3 `npm run lint` fails — CONFIRMED

Three `react-hooks/set-state-in-effect` errors, at
`Frontend/src/pages/Cases.jsx:54` and `:68`. I configured ESLint and then never
ran it.

---

## E. Tests

### E.1 The tests never exercise the migrations — CONFIRMED

`tests/conftest.py:35` builds the schema with
`Base.metadata.create_all(bind=engine)`.

`DECISIONS.md` says:

> *"I did have `create_all()` in `main.py` while I was still building the
> models, and I removed it once Alembic was working."*

I removed it from the application and left it in the tests, which is the half
that matters. The schema under test is generated from the models, not from the
migrations — so a migration that is broken, missing, or has drifted from the
models still passes all 183 tests. NF-02 is the requirement this weakens, and it
is the requirement the tests were meant to protect.

**Fix:** replace `create_all` with an `alembic upgrade head` in a session-scoped
fixture. It costs one fixture and turns NF-02 into something the suite proves
rather than something I assert.

### E.2 The suite takes 3.5 minutes, not "a few seconds" — CONFIRMED

```
183 passed in 209.29s
```

`DECISIONS.md` says dropping the tables between tests *"makes the suite a few
seconds slower and I think that is worth it."* The trade-off is still worth it;
the number is wrong by two orders of magnitude. Most of the cost is
`drop_all`/`create_all` per test plus a bcrypt hash per fixture.

### E.3 No test for `upgrade → downgrade → upgrade` — CONFIRMED

`DECISIONS.md` claims I verified the downgrade path. I did, by hand, when there
were two migrations. There are six now and nothing re-checks it.

### E.4 `test_query_count.py` sends a parameter that does not exist — CONFIRMED

Lines 60, 78 and 82 call `/cases?page=1&limit=...`. There is no `page`
parameter — the API uses cursor paging — so FastAPI ignores it silently. It is a
leftover from the offset-paging version, sitting in the one test the brief
explicitly asks for.

---

## F. API design

### F.1 `/docs` cannot authenticate — CONFIRMED

```
openapi.json -> components.securitySchemes: None
/clients parameters: [('search', False), ('before', False),
                      ('limit', False), ('token', False)]
```

Because auth is `token: str = Header(None)`, three things follow:

- the OpenAPI document declares no security scheme, so Swagger UI has **no
  Authorize button** — the interactive docs cannot call a protected route
- `token` appears on every route as an ordinary header parameter
- it is marked `required: false`, so the published spec says authentication is
  optional on every endpoint, which is the opposite of US-03

`DECISIONS.md` justifies choosing a JWT, but never the decision to carry it in a
custom `token` header instead of `Authorization: Bearer`. That is the choice with
the real cost, and it is the undocumented one.

**Fix:** `APIKeyHeader(name="token")` keeps the current header and registers a
proper security scheme; `HTTPBearer` is the standard option if I am willing to
change the header. Either way it is a dependency swap, not a rewrite.

### F.2 Bare `except:` in `verify_token` — CONFIRMED

`src/security.py` catches everything — `KeyboardInterrupt`, `SystemExit`, and any
typo inside the `try` — and reports all of it as 401.
**Fix:** `except JWTError:`.

### F.3 Config has no validation — unverified

`src/config.py` reads four values with `os.getenv` and defaults every one of them
to `None`. A missing `.env` produces `create_engine(None)` and
`allow_origins=[None]` rather than a message naming the missing key. NF-01 is
about someone else getting this running on their machine, and this is the first
thing that would meet them if they skipped the copy step.

**Fix:** `pydantic-settings` with required fields, so it fails at startup and
says which key is missing.

### F.4 A `DECISIONS.md` claim is contradicted by the code — CONFIRMED

> *"switching is a `DB_URL` change plus a driver"*

Two things say otherwise:

- `src/database.py:11` hardcodes `connect_args={"check_same_thread": False}`,
  which is SQLite-only and raises on Postgres
- `src/security.py` compares `Staff.id` (Integer) against `sub` (a string).
  SQLite coerces it; Postgres will not

The reasoning in that entry is sound — the closing sentence overstates it. It
should say what would actually have to change.

### F.5 A nonsense status returns 409, not 422 — CONFIRMED

```
PATCH /cases/1/status {"status":"Banana"}
  ->  409 "Cannot change status from Intake to Banana"
```

Already admitted in `DECISIONS.md` as "the next thing I would fix". It is a
one-line change — `status: Literal["Intake","Active","Settled","Closed"]` — which
also gives Swagger a dropdown. Knowing about it and not doing it is harder to
defend than not having noticed.

### F.6 `change_password` returns 403 — CONFIRMED

`src/routers/auth.py:176`. My NF-05 table lists 401, 404, 409 and 422. I
justified `require_admin`'s 403 in `DECISIONS.md`; this one is not justified
anywhere and should be 401 or 422.

### F.7 A missing token reports "Invalid or expired token" — CONFIRMED

```
GET /clients (no header) -> 401 {"message": "Invalid or expired token"}
```

Nothing was invalid — nothing was sent. Misleading while debugging.

### F.8 `GET /staff` exposes every colleague's email — CONFIRMED

`src/routers/auth.py:56` returns `StaffOut` (id, name, email, role) for every
account, to every authenticated user. The assignee picker needs id and name.

### F.9 An assignee sees the client name and the owner's email — CONFIRMED

```
as the assignee: GET /cases
  -> client: {"id":1,"name":"Ramesh Kumar"}, owner.email: "ali@example.com"
  -> GET /clients/1 as the same user: 404
```

Widening visibility to the assignee was deliberate and is documented. What I did
not think through is what rides along in `CaseOut`: the client's name and the
owner's **email address**, to someone who is explicitly not allowed to open that
client. The 404 on the client is correct; the leak is in the list payload.

**Fix:** give the owner a minimal shape without the email, and consider the same
for the client name when the caller is only the assignee.

### F.10 Non-RESTful route names

`POST /clients/registration` and `POST /cases/registration` where the convention
is `POST /clients` and `POST /cases`. Cosmetic, and not worth a breaking change
now, but worth naming as a choice rather than an accident.

---

## G. Frontend

### G.1 `Clients.jsx` does not URL-encode the search term — CONFIRMED

```js
// Cases.jsx:81
if (search) url += `&search=${encodeURIComponent(search)}`;   // correct

// Clients.jsx:34
let url = `/clients?search=${search}&limit=${LIMIT}`;         // not encoded
```

Searching a client whose name contains `&`, `#` or `+` breaks the query string.
The comment in `Cases.jsx` even explains why the encoding is needed — I fixed it
in one file and not the other.

### G.2 `validateStatus: () => true` plus partial status checks — CONFIRMED

`Frontend/src/api.js:9` makes every response, including 500s, resolve normally.
Several pages then check only for 401 and use the body directly:
`Cases.jsx:91`, `Clients.jsx:45`, `ClientDetail.jsx:37`, `NewCase.jsx:41`.

On any other error status `res.data.items` is `undefined`, `setState` stores
`undefined`, and the next `.map` throws — a blank page with no message. Combined
with A.1 this is reachable, not theoretical.

**Fix:** handle the non-200 case in `apiCall` itself, or guard every read.

### G.3 Hardcoded `limit=100` silently truncates two lists — CONFIRMED

- `ClientDetail.jsx:36` fetches `?client_id=${id}&limit=100` and then renders
  `Cases ({cases.length})`. Past 100 cases the heading is simply wrong, with no
  indication that anything was cut
- `NewCase.jsx:31` fetches `/clients?limit=100` for the client picker. The 101st
  client cannot be selected and the user is given no reason why

The seed gives Ali 65 clients, so neither shows up in the demo.

### G.4 Delete confirmation exists on two screens out of four — CONFIRMED

| Action | Confirms |
|---|---|
| Clients list → Delete (`Clients.jsx:72`) | yes |
| Staff list → Remove (`StaffList.jsx:119`) | yes |
| Client detail → Delete (`ClientDetail.jsx:45`) | **no** |
| Case detail → Delete note (`CaseDetail.jsx:135`) | **no** |

There is no undelete endpoint anywhere, which is the argument for confirming on
all four.

### G.5 The client link in the case list always 404s for an assignee — CONFIRMED

`Cases.jsx:236` links the client name to `/clients/{id}`. An assignee can see the
row but cannot open the client, so for them the link is guaranteed to land on
"Client not found". Related to F.9 — the name should probably not be there at all
for that user.

### G.6 `window.location.reload()` to refresh the sidebar — CONFIRMED

`Profile.jsx:38` — `setTimeout(() => window.location.reload(), 600)` after saving
a name, so that `Layout` re-fetches `/me`. A full page reload inside a
single-page app, to move one string.

### G.7 Two different `setState` styles for the same job — CONFIRMED

`Clients.jsx:87` uses `setRefresh(refresh + 1)`; `CaseDetail.jsx:79` and
`StaffList.jsx:112` use `setRefresh((n) => n + 1)`. The functional form is the
correct one.

### G.8 The API base URL is hardcoded — CONFIRMED

`api.js:4` — `"http://127.0.0.1:8000"`. The backend reads its origin from `.env`
while the frontend has the address compiled in. It should be
`import.meta.env.VITE_API_URL`, with a `Frontend/.env.example` to match.

### G.9 No shared handling for an expired token — CONFIRMED

The token expires after 30 minutes. Every page implements its own 401 branch and
several omit it. This is the same argument I made for `owned_by` on the backend —
one place instead of nine — and I did not apply it here. An axios response
interceptor would do it once.

---

## H. Documentation that no longer matches the code

| Where | Says | Actually |
|---|---|---|
| `README.md` | "143 tests" | 183 |
| `README.md` API list | omits `PATCH /staff/{id}`, `DELETE /staff/{id}`, `/admin/cases` | all three exist |
| `README.md` `GET /cases` | omits `&search=` | the parameter exists |
| `README.md` | `python run.py` as the documented command | it hardcodes `reload=True`, a development-only flag |
| `DECISIONS.md` | "switching is a `DB_URL` change plus a driver" | see F.4 |
| `DECISIONS.md` | dropping tables costs "a few seconds" | 209 seconds (E.2) |

`DECISIONS.md` also runs to 21 entries of several paragraphs each, where the brief
asked for five to ten in a one-line / one-line / two-or-three-line shape. I do not
think the reasoning is wasted, but I did not follow the format I was given.

---

## I. Comments and hygiene

There are roughly 158 Hinglish comment lines mixed in with English ones across the
backend, the frontend and the migration docstrings. The mix itself is the problem —
a reader gets one language or the other depending on the file.

Two comments are notes-to-self rather than comments and should not have been
committed:

- `src/models/case.py:31` — a stream-of-consciousness line ("...OKK like and then
  last_assignment mein sorf ek return kar rahe hai thats why")
- `src/models/case.py:21` — a paragraph explaining what a SQLAlchemy
  `relationship` is, which documents the library rather than this code

Three migration docstrings are also in Hinglish, and migrations are the files most
likely to be read years later by someone else.

Two smaller things: there are two virtualenvs (`.venv` at the root, without pytest,
and `Backend/venv`, with it), so the README's bare `pytest` fails depending on
which is active; and `CASEDESK_PROJECT.md` — the brief itself — is committed into
the repository.

---

## What I would fix first

Ordered by cost against what it buys.

| # | Fix | Est. | Why first |
|---|---|---|---|
| 1 | `Query(ge=1, le=100)` on `limit` and `before` | 5 min | Closes a live 500 (A.1, A.2) |
| 2 | Register a security scheme so `/docs` can authenticate | 15 min | The docs are the first thing anyone opens (F.1) |
| 3 | Delete `/admin/cases` | 2 min | 45 dead lines that contradict my own reasoning (D.1) |
| 4 | Finish `version` or remove it entirely | 20 min | A half-built feature is worse than an absent one (B.2) |
| 5 | Validate phone | 10 min | A stated acceptance criterion (B.1) |
| 6 | `deleted_at` filter on the three staff lookups | 5 min | My own removal rule is bypassable (C.1, C.2) |
| 7 | `min_length` / `max_length` across write schemas | 15 min | Empty and unbounded input (B.3) |
| 8 | Escape `%` and `_` in search | 10 min | Search returns wrong results (B.4) |
| 9 | `Literal` on the status field | 3 min | Turns the 409 into a 422 and documents itself (F.5) |
| 10 | conftest: `create_all` → `alembic upgrade head` | 20 min | Makes NF-02 something the suite proves (E.1) |
| 11 | Reject explicit nulls on required fields | 10 min | Closes a second 500 (C.3) |
| 12 | `encodeURIComponent` in `Clients.jsx` | 1 min | One line (G.1) |
| 13 | Remove the leftover junk | 10 min | The cheapest quality signal there is (D.2) |
| 14 | Correct the README and `DECISIONS.md` claims | 15 min | Docs that are wrong are worse than absent (H, E.2, F.4) |
| 15 | Fix the three ESLint errors | 15 min | `npm run lint` should pass (D.3) |

The rest — the frontend confirmations, the reload, 403 vs 401, the hardcoded
limits, the comment languages — are worth discussing rather than rushing.

---

## The pattern underneath most of this

Three of the findings are not isolated mistakes but the same one:

- `DECISIONS.md` argues that a shared filter beats nine hand-written checks — and
  `/admin/cases` is 45 duplicated lines (D.1)
- `DECISIONS.md` says `create_all()` was removed — it is still in the test
  fixtures, which is the half that mattered (E.1)
- I wrote the reason for `encodeURIComponent` in one file and left the other
  unencoded (G.1)

In each case I understood the rule, wrote it down, and then did not apply it
consistently. That gap between what I documented and what the code does is the
thing I most want to close, because it is worth more than any individual fix in
this list.

---

## Second round - found by running it, not reading it

The list above came from re-reading my own code. Everything below came from
actually calling the API and querying the seeded database, which is why none of
it appears above: reading does not catch a rule that was never written.

| # | Issue | Severity |
|---|---|---|
| J.1 | Removing a staff member ignored assigned cases, only owned ones | High |
| J.2 | `PATCH /cases/{id}/status` did not move `version`, so the US-21 check could be walked straight past | High |
| J.3 | `StaffRegister` had no `max_length=72`, so bcrypt silently truncated and any tail after 72 characters logged in | High |
| J.4 | No `DELETE /cases/{id}` at all, which made any client who had ever had a case permanent | High |
| J.5 | A closed case refused notes but accepted title, type and assignee changes | Medium |
| J.6 | Changing a password left every existing token working | Medium |
| J.7 | `ClientOut` carried no owner, so an admin could set "Belongs to" and never see it again | Medium |
| J.8 | `NewClient.jsx` filtered the picker on `role`, which `/staff` does not send - the dropdown was always empty | Medium |
| J.9 | No `Exception` handler, so a 500 came back outside the NF-05 envelope | Medium |
| J.10 | `?assignee=0` dropped the filter instead of rejecting it (`0` is falsy in Python) | Medium |
| J.11 | `?status=Banana` was 200 on the list and 422 on the PATCH - one value, two answers | Low |
| J.12 | `StaffList.jsx` and `EditClient.jsx` used `res.data` without checking `res.ok` | Medium |
| J.13 | No screen ever called `PATCH /cases/{id}` for title or type - the endpoint and its tests existed, the UI did not | Medium |
| J.14 | Seed: `60 - i` went negative past 60 cases, putting 11 history rows in the future | High |
| J.15 | Seed: `Case.created_at` was never backdated, so cases were created a month after their own history closed them | High |
| J.16 | Seed: 38 notes sat on closed cases, a state the API itself refuses | Medium |
| J.17 | `update_client` did not lowercase email; `client_registration` did | Low |
| J.18 | No index on any foreign key - every ownership filter was a full scan | Medium |
| J.19 | README claimed US-21 was unimplemented and the seed made 30 and 10 cases (it makes 60 and 19) | Medium |
| J.20 | `DECISIONS.md` claimed `StaffRegister` had `max_length=72`. It did not - see J.3 | High |

J.20 is the one worth saying out loud. The doc described a security control that
was never written, so re-reading the doc could only ever confirm it was there.
That is the failure mode of writing decisions ahead of the code instead of
alongside it.

### Still open, deliberately

- **`/cases` loads the full history of every case on the page.** `selectinload`
  keeps the query count flat, which is what US-20 asks for and what
  `test_query_count.py` measures, but a case with fifty events fetches all fifty
  to display the newest one. A `max(id)` subquery would fix it. Left alone at
  this size, and written down in the README rather than quietly.
