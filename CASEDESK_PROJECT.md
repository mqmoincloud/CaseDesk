# CaseDesk — Mini Case-File Manager

**Project brief**

---

## Overview

CaseDesk is a small internal web application for a law firm's staff. A staff member records **clients**, opens **cases** against those clients, and logs **notes** on each case.

You will build the whole thing: database, API, and a simple web interface. Everything runs locally on your own machine — there is nothing to deploy.

The domain is intentionally simple. The value of the project is in getting the details right: correct data isolation between users, honest deletions, lists that page and filter properly, and a repository that someone else can clone and run without asking you a single question.

---

## Technical choices

The API is built with **FastAPI**. Everything else is yours to decide — database, ORM, migration tool, authentication mechanism, test framework, and how you build the front end.

Choose deliberately rather than by default, and record each choice in `DECISIONS.md`: what you picked, what you passed over, and why. The constraints that apply regardless of what you choose are in the **Non-functional requirements** section below — read those before you decide.

Keep the front end deliberately plain. Styling is not part of the brief.

---

## Data model

Four tables. Design the columns yourself.

```
User  ──< Client ──< Case ──< Note
                       │
                       └──> assigned to a User
```

- **User** — a staff member who logs in.
- **Client** — a person the firm represents. Belongs to the user who created them.
- **Case** — belongs to a client, has a status and an assignee.
- **Note** — belongs to a case, has an author and a timestamp.

---

## Epic 1 — Accounts and access

### US-01 — Register
*As a staff user, I want to create an account with an email and password so that I can use the system.*

- Passwords are stored hashed (bcrypt or argon2). Never store a password in plaintext or in a form that can be decrypted.
- Registering with an email that already exists returns `409`.
- A password below the stated minimum length returns `422` with a field-level error.

### US-02 — Log in
*As a staff user, I want to log in and receive a credential so that my later requests are authenticated.*

- A successful login returns whatever credential your chosen mechanism uses — a bearer token, a signed session cookie, something else. Your call, recorded in `DECISIONS.md`.
- Whatever it is, it identifies the user, expires, and cannot be forged or edited by the client.
- A wrong password and an unknown email return the **same** `401` message. Do not reveal which accounts exist.
- An expired or tampered credential returns `401`.

### US-03 — Protected endpoints
*As the business, I want every data endpoint to require authentication so that nothing is reachable anonymously.*

- Every `/clients`, `/cases` and `/notes` route returns `401` when the credential is missing, malformed, or expired.

---

## Epic 2 — Clients

### US-04 — Create a client
*As a staff user, I want to add a client with name, phone, email and address so that I can open cases for them.*

- Name is required. Phone and email are format-validated when present.
- `created_at` and `updated_at` are set automatically, in UTC.

### US-05 — View a client
*As a staff user, I want to open a client and see their details together with all of their cases so that I have the full picture in one place.*

### US-06 — Edit a client
*As a staff user, I want to update a client's contact details so that the record stays current.*

- `updated_at` changes on every update; `created_at` never does.
- A partial update must not blank out fields that were not sent.

### US-07 — Delete a client
*As a staff user, I want to remove a client I entered by mistake so that my list stays clean.*

- Deletion is **soft**: the row stays in the database with a `deleted_at` timestamp.
- See US-16 for what a deletion must mean across the rest of the application, and US-19 for what happens when the client already has cases.

### US-08 — List and search clients
*As a staff user, I want to search my clients by name, phone or email so that I can find someone quickly.*

- Search is case-insensitive and matches partial strings.
- Results are paginated and include a correct total count.

---

## Epic 3 — Cases

### US-09 — Open a case
*As a staff user, I want to open a case against a client with a title, type, status and assignee so that the work can be tracked.*

- A case must reference an existing, non-deleted client that belongs to me.
- New cases start at status `Intake`.

### US-10 — View and edit a case
*As a staff user, I want to open a case and see its details, its client, and its notes so that I can work on it.*

### US-11 — List and filter cases
*As a staff user, I want to filter cases by status and by assignee so that I can see what is on my plate.*

- Filters combine: applying status **and** assignee narrows the result to both, rather than one overriding the other.
- The list displays the client's name and the assignee's name.

### US-12 — Close a case
*As a staff user, I want to mark a case closed so that it drops out of my active list.*

---

## Epic 4 — Notes

### US-13 — Add a note
*As a staff user, I want to append a dated note to a case so that there is a record of what happened.*

- Notes appear newest-first on the case detail page.
- Author and timestamp are taken from the authenticated user on the server, never from the request body.

### US-14 — Delete a note
*As a staff user, I want to remove a note I added by mistake.*

- Only notes on cases I own can be deleted.

---

## Epic 5 — Data isolation and deletion integrity

### US-15 — Ownership isolation
*As a staff user, I want my clients and cases to be invisible to other staff so that data does not cross between users.*

- Requesting a client, case or note that belongs to another user returns `404` — not `403`, and not the record. A `403` confirms the record exists, which is itself a leak.
- The same applies to update and delete, not only to read.
- **This includes search.** Searching a term that matches another user's client must return no results.
- Verify by signing in as User A and calling every endpoint with User B's ids. Nothing should come back.

### US-16 — Soft delete honoured everywhere
*As a staff user, I want a deleted client to disappear from the entire application so that I never act on stale data.*

A deleted client must not appear in any of these:

1. The client list
2. Search results
3. The total count returned with a list
4. The client column of the case list
5. Any client picker or dropdown in the UI

- A deleted client's id must also be rejected when creating a new case.
- Verify all six points, not just the first.

### US-17 — Pagination, filtering and search that agree with each other
*As a staff user, I want paged lists to be trustworthy so that I never miss a record.*

- Ordering is stable and deterministic. Inserting a record while paging must not cause a duplicate or a skipped row.
- The returned `total` reflects the **filtered** set, not the size of the whole table.
- `has_next` (or equivalent) is correct on the final page.
- Verify with at least 60 records, a filter applied, paged from the first page to the last.

---

## Epic 6 — Data rules

### US-18 — Case status transitions
*As the business, I want case status to follow a defined lifecycle so that records cannot end up in a nonsense state.*

- Allowed path: `Intake → Active → Settled → Closed`.
- `Closed` is terminal — a closed case cannot be reopened.
- Skipping a step (for example `Intake → Closed`) returns `409`.
- Enforce this in the API. Hiding the buttons in the UI is not enough — the rule must hold for any caller.

### US-19 — Deleting a client who has cases
*As the business, I want a defined answer for what happens to a client's cases when the client is deleted.*

- You choose the behaviour: either **block** the delete with `409`, or **cascade** the soft-delete to their cases.
- Whichever you choose must be applied consistently and covered by a test.
- Record the decision in `DECISIONS.md`: what you chose, what you rejected, and why.

### US-20 — Efficient list queries
*As the business, I want list endpoints to stay fast as data grows.*

- Listing 50 cases together with client name and assignee name must issue a small, constant number of database queries — not one query per row.
- Verify by turning on query logging and counting the statements actually issued for a 50-row page.

### US-21 — Concurrent edit protection *(stretch, optional)*
*As a staff user, I want to be warned rather than silently overwritten when someone else has edited the same case.*

- Add a `version` column that increments on each update.
- An update carrying a stale version returns `409` instead of overwriting.

---

## Epic 7 — Screens

### US-22 — Usable interface
*As a staff user, I want screens for the things I do daily so that I am not using curl.*

Build these:

- Login screen
- Client list with a search box
- Client create / edit form
- Client detail, showing that client's cases
- Case list with status and assignee filters
- Case detail, showing notes and an add-note box

Plain HTML is fine. Correct behaviour matters; visual polish does not.

---

## Non-functional requirements

**NF-01 — Runs from a fresh clone.**
One documented command must bring up the database, apply migrations, seed demo data, and start the server. Someone cloning your repository on a different machine should reach a working app without asking you anything. Test this by cloning into a clean folder yourself.

**NF-02 — Migrations.**
All schema changes go through versioned migration files, applied by a tool. Dropping and recreating the database is not a migration strategy.

**NF-03 — Real database in tests.**
Integration tests run against an actual database, not a mocked session.

**NF-04 — Seed data.**
Provide a seed script creating **two** staff users, and enough clients, cases and notes that pagination, filtering and isolation can be exercised meaningfully — 60+ records.

**NF-05 — Consistent error contract.**
One error shape across the whole API, with correct status codes:

| Code | Meaning |
|---|---|
| `401` | Not authenticated |
| `404` | Not found, or not yours |
| `409` | Conflict — duplicate, or a disallowed state change |
| `422` | Validation error |

**NF-06 — Time.**
All timestamps stored timezone-aware, in UTC. Convert for display only.

**NF-07 — Secrets.**
No credentials committed. Provide a `.env.example`; keep `.env` gitignored.

---

## Out of scope

Do not build any of these — they are deliberately excluded:

- Any cloud deployment. This runs locally only.
- Email, SMS or notifications of any kind
- Roles or permission levels beyond "owns it or doesn't"
- File uploads or document storage
- Reporting, charts or dashboards
- Audit logging
- Multi-firm tenancy

---

## Definition of Done

A story is finished when all of the following are true:

1. Its acceptance criteria pass under an automated test.
2. Migrations run cleanly against an empty database.
3. Previously finished stories still pass — nothing has regressed.
4. Any non-obvious decision has an entry in `DECISIONS.md`.
5. You can explain the code out loud, without notes — in particular, where authorisation is enforced and why it lives there.

---

## Suggested schedule

| Day | Focus |
|---|---|
| 1 | Project skeleton, schema, migrations, seed script, auth (US-01–US-03), clients (US-04–US-08) |
| 2 | Cases and notes (US-09–US-14), first screens (US-22) |
| 3 | Isolation and deletion integrity (US-15–US-17) |
| 4 | Data rules (US-18–US-20), screen cleanup |
| 5 | Fresh-clone verification, README, `DECISIONS.md`, tidy-up |

There is a short review session at the end of each day. Bring a running app, not a branch you are midway through.

---

## Deliverables

At the end of the week your repository should contain:

- [ ] Working application, startable with one documented command
- [ ] Migration files
- [ ] Seed script
- [ ] Test suite covering the acceptance criteria above
- [ ] `README.md` — setup, how to run, how to run the tests
- [ ] `DECISIONS.md` — see below
- [ ] `.env.example`

### About `DECISIONS.md`

Keep a running log — five to ten short entries is right. Each entry:

> **What I decided** — one line
> **What I rejected** — one line
> **Why** — two or three lines

Write an entry whenever you make a call that another reasonable developer might have made differently. At minimum: your stack choices (database, ORM, migrations, auth, tests, front end), how you enforce ownership, how you model soft delete, how you handled US-19, and how you solved the query-count problem in US-20.

Start the first few entries on day 1, while you are choosing the stack — those are the decisions hardest to reconstruct later.

---

## Working notes

**Use AI assistants freely.** They are part of how the work gets done. Two expectations come with that:

1. **You own the code.** If you cannot explain a line, do not commit it. You will be walking through your own code at the end of the week.
2. **Write the decisions down as you go**, not on Friday afternoon. The reasoning is the part that is hard to reconstruct later.

**Commit as you work**, in small pieces, with real messages. A single giant commit at the end is harder for anyone to read — including you.

**Ask questions.** Anything in this brief that is ambiguous, contradictory, or looks wrong: ask. Noticing an ambiguity is useful; guessing silently is not.
