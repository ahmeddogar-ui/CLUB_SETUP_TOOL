# Architecture

Club Setup Tool is one service: a FastAPI backend that serves a JSON API under
`/api` and the built React app at every other path, backed by Postgres.

```
browser ──► FastAPI ──┬─ /api/...            routers → services → SQLAlchemy → Postgres
                      ├─ /health, /dbhealth  liveness and database checks
                      └─ any other path      frontend/dist (index.html for page navigations)
```

In development Vite serves the React app on port 5173 and proxies `/api` to
FastAPI on port 8000, so the frontend calls the same `/api/...` paths in both
setups.

## Backend (`app/`)

| Path | Role |
| --- | --- |
| `main.py` | Builds the app: the domain-error handler, health checks, the `/api` router, and FastAPI's `app.frontend` serving `frontend/dist` |
| `routers/` | HTTP only: parse the request, call one service function, return a schema. `auth`, `clubs`, `requirements`, `comments`, `users`, `activity`, `requests` (and `/rooms`) |
| `services/` | Business rules: `auth`, `clubs`, `requirements`, `comments`, `users`, `activity`, `requests`. No FastAPI imports |
| `request_types.py` | Request types as data: each type's form fields (a details model) and its ordered approval steps |
| `request_transitions.py` | The one request state machine every type shares |
| `listing.py` | What every paged list shares: `Page`, `paginate` (items + count) and `contains` (escaped `ILIKE`) |
| `transitions.py` | The club state machine: which status changes are allowed, by whom, and their guards |
| `models.py` | SQLAlchemy tables, enums and constraints |
| `schemas.py` | Request/response shapes and every input limit (named constants) |
| `exceptions.py` | `NotFound`, `Forbidden`, `Conflict`, `Unauthorized`, raised by services |
| `core/config.py` | Settings, read once from the environment or `.env` |
| `core/security.py` | Password hashing, JWTs, and the `get_current_user` / `require_role` dependencies |
| `seed.py`, `cli.py` | `make-admin` (the fallback for granting the admin role) and `seed-demo` operator commands |

Every schema change is an Alembic migration in `alembic/` at the repo root.

### Rules the code follows

- **Dependencies point inward.** Routers import services; services never raise
  HTTP errors or use FastAPI's routing. A service raises a domain error
  (`Conflict("Cannot move drafting -> approved")`) and the single handler in
  `main.py` turns it into a status code. (`services/auth.py` does use the
  hashing and token helpers in `core/security.py`, a module that also holds the
  FastAPI auth dependencies.)
- **One state machine.** `transitions.ALLOWED` lists every legal
  `(from, to)` status move and the role that may make it. An illegal move is a
  409; the wrong role is a 403. Guards (documents provided, all requirements
  approved, a note for rejecting or requesting changes) live next to it in
  `_check_guards`.
- **Every write locks the club row first.** `get_club_for_update` loads the club
  with `SELECT … FOR UPDATE`; every service that changes an existing club or
  its requirements starts there. Two requests on one club therefore run one after
  the other, and the second sees the first's result. Before the lock, ten
  parallel submits all succeeded; `tests/test_concurrency.py` now proves
  exactly one does.
- **One transaction per request.** `get_db` (`database.py`) opens a session per
  request and rolls back if anything raises; each service commits once, so a
  status change and its history event are saved together or not at all.
- **One permanent history.** `events` is the app's only log, and append-only: a
  database trigger rejects `UPDATE` and `DELETE`, and its foreign keys are
  `RESTRICT`, so nothing with history can be deleted either. Every action
  writes one row in the same commit as the change it records: club and
  requirement steps, comments, role changes and request actions. A club's
  history, its discussion, a request's history and the admin's activity log
  are all queries over it. `EventType` names the vocabulary.
- **Validate at the edge.** Pydantic schemas trim and bound every string
  (`schemas.py`); the database adds enums, unique constraints, a lowercase-email
  check and foreign keys. Services trust their input.

### Data model

`users` (role `admin`, `club_lead` or `finance_approver`) → `clubs` (one
submitter, one status) → `requirements` (six per club, created with the club:
four document links and two checklist items) and `requests` (see Requests).
`events` holds the history: each row is about a club (`club_id`) or, for a
role change, a user (`subject_user_id`); a check constraint
(`about_club_or_user`) requires one of them. Request events also carry
`request_id`, requirement events `requirement_id`. Indexes serve each view of
it: `idx_events_club_time` (a club's history and comments),
`idx_events_request_time`, and for the activity log `idx_events_time`,
`idx_events_actor_time` and `idx_events_type_time`, all newest first.
`refresh_tokens` stores SHA-256 hashes of login tokens.
`idx_clubs_status_updated` serves lists filtered by status and sorted by last
update (the review queue and the admin's status tabs),
`idx_clubs_submitter_updated` a lead's own list, and `idx_clubs_updated
(updated_at, id)` the admin's All tab, newest first (Postgres scans it
backwards). Name and owner sorts are unindexed: they are occasional, and a
sort over a few thousand rows is cheap.

### Club lifecycle

```
drafting ─submit─► submitted ─start review─► under_review ─┬─approve────────► approved
                       ▲                                    ├─reject─────────► rejected
                       └──resubmit── changes_requested ◄────┴─request changes
```

Leads submit and resubmit; admins do everything else. While a club is
`under_review`, admins approve or reject each requirement; the club can only be
approved once all six are approved.

### Listing clubs

`GET /api/clubs` returns one page: `{items, total, status_counts}`. It takes
`status` (repeatable), `sort` (`name`/`owner`/`status`/`updated`) with
`order` (`asc`/`desc`), `q` (case-insensitive name search; `%` and `_` match
literally), `limit` (1–100, default 20) and `offset`. Without `sort` the order
is creation order. Name and owner sort case-insensitively; status sorts in
lifecycle order, because Postgres orders an enum by declaration. `id` breaks
ties in the same direction, so `asc` and `desc` are exact reverses and paging
never repeats or skips a club.
Each item adds `owner_name`, `updated_at` and `documents_provided` /
`documents_total` to the club. A page costs three queries whatever its size:
the items (owner join plus correlated document counts), the filtered `total`,
and one `GROUP BY status` for `status_counts`, which covers every club the
user can see and ignores the filters. A document counts as provided while it
is `submitted` or `approved` (`DOCUMENT_PROVIDED_STATUSES`, shared with the
submit guard). A club's `updated_at` moves on every status change, edit and
new document link; reviewing a requirement doesn't move it, so the review
queue's "waiting" time is the time since the last status change.

`GET /api/clubs/export.csv` (admins only) returns every club matching the same
`status`, `q`, `sort` and `order` filters as the list, unpaged, through the same
filtering and summary query (`export_clubs`). The CSV is rendered in the router
because it is a transport format, not business logic; the service returns the
same `ClubSummary` rows the list uses. Text cells (club and owner names, which
users control) that start with `=`, `+`, `-`, `@`, tab or carriage return get a
leading `'`, so a spreadsheet shows them as text instead of running them as a
formula.

### Requests

Once a club is approved, its lead can file requests: funding and room
bookings so far. Club registration stays its own workflow (`transitions.py`),
because it creates the club; requests are one generic engine.

- **Types are data.** `request_types.py` gives each type its form fields (a
  Pydantic details model, validated at the edge, discriminated by
  `request_type`) and its ordered approval steps: funding is admin, then
  finance approver; a room booking is admin. Adding a type means adding its
  fields and steps there, and where its data is stored (`_store_details`);
  the state machine, approvals, locking, history and the UI's actions don't
  change.
- **One state machine.** `request_transitions.ACTIONS` lists each action, the
  statuses it may start from, and who may take it: the club's lead
  (`submit`, `cancel`) or the approver of the current step (`start_review`,
  `approve`, `reject`, `request_changes`).

  ```
  draft ─submit─► submitted ─start review─► in_review ─approve (last step)─► approved
    ▲                                         │ ├─approve (more steps): stays in_review
    └──────── submit ◄── changes_requested ◄──┤ ├─request changes
                                              └─┴─reject───────────────────► rejected
  The lead can cancel anything not yet decided, and an approved booking
  that hasn't started.
  ```
  Checks run in a fixed order: can this user see it (403), does the action fit
  the status (409), may this user take it (403), and the rules about time and
  money (409, `_refusal`): a booking whose time has come can't be submitted,
  reviewed or approved, and approved funding (perhaps already paid) or an
  approved booking that has started can't be cancelled, because either would
  rewrite what happened.
- **Approvals.** `request_approvals` has one row per approved step: who, when,
  an optional note. The API returns the current round's; earlier rounds stay
  in the table and in the request's history. `UNIQUE (request_id, round, step)` makes a second
  approval of one step impossible. The request is approved when the last
  step is. Every submit starts a new `round`, so after changes are requested
  every step approves again; earlier rounds stay on record.
- **Who it waits for.** `requests.awaiting_role` is the current step's role,
  set exactly while `submitted` or `in_review` (a check constraint). It is
  derivable from the steps and this round's approvals, but storing it makes
  the review queue one indexed query (`idx_requests_awaiting_updated`).
- **Who sees it.** The club's lead, and anyone who approves a step of its type:
  admins see every request, finance approvers only funding. The same rule is a
  Python check (`_can_see`) and a SQL filter (`_visible_to`).
- **The UI never re-derives rules.** Each request comes with `allowed_actions`
  and `can_edit` for the viewer, computed by the same code that enforces them.
- **Locks.** Like clubs, every write locks the request row (`FOR UPDATE`) and
  commits once with its event, so concurrent approvals queue and the second
  sees the first's result. `test_request_concurrency.py` fires two approvals
  of one step: one succeeds.
- **Funding** stores `funding_line_items` (description, `amount_cents > 0`)
  in whole cents, so totals are exact; the total is a `SUM`, never stored.
- **Room bookings** live on the request row: `room_id` and `booked_during`, a
  `tstzrange` stored `[start, end)` so back-to-back bookings fit. Check
  constraints require both exactly for bookings, and a non-empty, bounded
  range. Bookings are at most 12
  hours and start in the future. `rooms` is reference data seeded by its
  migration.

#### No double booking

The database guarantees it, not the application:

```sql
EXCLUDE USING gist (room_id WITH =, booked_during WITH &&)
  WHERE (status IN ('submitted', 'in_review', 'changes_requested', 'approved'))
```

Two bookings of one room can't overlap while both hold the slot. A draft holds
nothing, so a lead can't block a room without submitting; rejecting or
cancelling frees it at once. `btree_gist` lets one GiST index combine `=` on
the room with `&&` on the range. Submitting, or moving a booking during
changes requested, into a taken slot fails the constraint, and the service
turns that violation into a 409: "DV 2074 is already booked for part of that
time. Choose another time or room."

Writes to a booking also lock the room's row first. Without it, two
transactions booking one slot each insert their row, then each waits on the
other's uncommitted row to check the constraint: Postgres aborts one as a
deadlock, an error instead of a clear 409. The room lock queues them, so the
second sees the first's committed booking and gets the clean violation. A
move between rooms locks the old and the new room in id order, so two leads
swapping rooms at once queue instead of deadlocking (also tested).
`test_request_concurrency.py` books one slot from 20 parallel transactions and
asserts exactly one succeeds.

### Users, roles and the activity log

- `GET /api/users` (admins) searches name or email and filters by role;
  `PATCH /api/users/{id}/role` changes a role and records a `role_changed`
  event ("Club lead → Admin"). An admin can't change their own role, so the
  last admin can't remove themselves; `change_role` locks the actor and the
  user in id order and re-checks the actor, so two admins demoting each other
  at once leave one admin. A lead who owns clubs stays a lead, because only a
  lead can submit their clubs. `make-admin` applies the same rule.
- `GET/POST /api/clubs/{id}/comments`: anyone who can see the club (its lead,
  admins) reads and posts. A comment is a `comment_posted` event with the body
  as its note, paged newest first.
- `GET /api/activity` (admins): every event, newest first, filtered by actor,
  club, event type and a date range (`since` inclusive, `until` exclusive).
  Names come from joins, so a page is two queries (items and count).

### Auth

- `POST /api/auth/login` checks the password (Argon2) and returns a 30-minute
  JWT access token. It also sets a 14-day refresh token in an `httpOnly`,
  `SameSite=strict` cookie (`Secure` when `SESSION_HTTPS_ONLY=true`).
- The frontend sends the access token as `Authorization: Bearer …`.
  `get_current_user` decodes it; `require_role(UserRole.admin)` guards admin
  routes before their body runs.
- `POST /api/auth/refresh` exchanges the refresh cookie for a new access token
  (the cookie itself is unchanged: there is no rotation);
  `POST /api/auth/logout` revokes it in the database.
- `PATCH /api/auth/me` renames the user. `POST /api/auth/me/password` needs
  the current password; a wrong one is a 403, not a 401, because the frontend
  treats a 401 as an expired session and signs out. Success revokes every
  other refresh token of the user, signing out their other devices once their
  access tokens expire (at most 30 minutes).
- Everyone who signs up is a club lead. Admins change roles on the users
  page; `python -m app.cli make-admin <email>` remains for the first admin.

## Frontend (`frontend/`)

React 19 + TypeScript + Vite + Tailwind, built on the TailAdmin template's UI
primitives (`src/components/ui`, MIT, see `frontend/LICENSE.md`).

| Path | Role |
| --- | --- |
| `src/main.tsx` | Entry point: query client, router, theme, auth providers |
| `src/App.tsx` | The only route table, and the one `Toaster` |
| `src/components/layout/app-layout/` | Sidebar (links per role) and header around every signed-in page |
| `src/components/shared/` | Route guards (`RequireAuth`, `RequireRole`), page title, logo, and what every list shares: `Pager`, `TableSkeleton`, `list-states` (error and empty), `NativeSelect` |
| `src/pages/main/clubs/` | Every club screen and its dialogs, the discussion and the review queue |
| `src/pages/main/requests/` | The club's Requests tab, new/edit request, request detail |
| `src/pages/main/users/`, `activity/`, `profile/` | Users and Activity (admins), Profile (everyone) |
| `src/pages/others/landing/` | `/welcome`, for signed-out visitors |
| `src/pages/others/auth/` | Sign in and sign up |
| `src/lib/api.ts` | `apiFetch()` for JSON and `apiDownload()` for files: the only ways to call the backend, sharing one request, refresh and error path |
| `src/lib/types.ts` | The backend's JSON shapes, mirroring `app/schemas.py` |
| `src/lib/limits.ts` | Input limits, mirroring `app/schemas.py` |
| `src/contexts/` | Auth (current user, sign in/out) and theme (light/dark) |

### Data fetching

TanStack Query handles all server data: `useQuery` to read, `useMutation` to
change. Query keys are `["me", token]`, `["clubs", "list", filters]` (every
club list: status, search, sort and page; built by `clubPageQuery`),
`["clubs", id]`, `["clubs", id, "requirements"]`, `["clubs", id, "events"]`,
`["clubs", id, "comments"]` (an infinite query: Show older comments),
`["requests", "list", filters]`, `["requests", id]`, `["users", "list",
filters]` and `["activity", filters]`.
Every club change goes through `useClubMutation`, which invalidates `["clubs"]`
so all club data refetches. Confirmation toasts (sonner) come from one place:
`createQueryClient()` (`src/lib/query-client.ts`) gives the `QueryClient` a
`MutationCache` whose `onSuccess` shows `mutation.meta.successMessage`, so a
mutation states its message and no component calls `toast` for success. The
tests build their client with the same function, so toasts are tested too.
`successMessage` may be a function of the mutation's variables ("Ada is now
Admin"). 4xx errors are not retried; 5xx and network errors retry up to
three times.

### Sessions and 401s

All 401 handling is in two places:

1. `apiFetch`: a 401 on a request that carried a token means the access token
   expired. It calls `/api/auth/refresh` once and retries. If the refresh fails
   too, it clears the token and dispatches a `session-expired` window event.
2. `AuthProvider`: listens for that event and signs out locally, clearing the
   token and the query cache. `RequireAuth` then sends the user to `/signin`
   (or, from `/`, to the landing page at `/welcome`).

An event is used because `apiFetch` is a plain module with no access to React
state; the auth context owns sign-out.

### Screens

| URL | Who | Page |
| --- | --- | --- |
| `/welcome` | anyone | Landing page: what the product does, sign in, sign up. A signed-out visit to `/` comes here |
| `/signin`, `/signup` | signed out | Sign in; register as a club lead |
| `/` | leads, admins | `clubs-page.tsx`: a lead's own clubs, or every club for an admin with status counts, status tabs and a name search. Status, search, sort and page are in the URL (`?status=&q=&sort=&order=&page=`); the column headers sort |
| `/clubs/new` | club leads | `new-club-page.tsx` |
| `/clubs/:clubId` | owner or admin | `club-detail-page.tsx`: Overview (details, requirements, actions, discussion, history) and Requests (`?tab=requests`: the club's requests, New request for the lead of an approved club) |
| `/clubs/:clubId/requests/new`, `/requests/:id/edit` | the club's lead | Funding (line items, live total) or room booking (room, date, times) |
| `/requests/:id` | lead, admins, finance (funding) | Details, the approval steps with who/when/note, exactly the viewer's `allowed_actions`, history |
| `/review` | admins, finance approvers | Clubs waiting for review (admins), and requests awaiting the viewer's role, oldest first. Finance approvers land here |
| `/users` | admins | Search, role filter, change a role |
| `/activity` | admins | Every event, newest first; click a person or club to filter by it; type and date filters |
| `/profile` | everyone | Change name and password |

The backend enforces every rule; the UI only hides buttons that would be
refused, and shows the backend's message when something is.

Every list pages through 20 clubs at a time, and every empty list says why
and offers a next step (create a club, clear the filters, go to the first page).
Lists keep the previous page as placeholder data (so the pager and counts
don't jump) but show skeleton rows over it while the next page loads, so a
stale page is never presented as current. Reject and request-changes take a
second, explicit confirmation that repeats the note: both notify the lead and
reject is final. Below the `md` breakpoint the clubs table drops its secondary
columns rather than scrolling sideways.

## Deployment

The `Dockerfile` builds the frontend in a Node stage, then copies
`frontend/dist` into a Python image that runs `alembic upgrade head` and
uvicorn. `render.yaml` deploys that image as one Render web service; the
database is Neon Postgres. See the README for the steps.

## Decisions and why

| Decision | Why | Rejected alternative |
| --- | --- | --- |
| One service serves the API and the built frontend | Same origin: no CORS, and the `SameSite=strict` refresh cookie just works | A separate static host plus CORS and a cross-site cookie |
| API under `/api`, no proxy rewrite | Identical paths in development and production | Rewriting `/api` away in Vite, which only exists in development |
| Row lock on the club for every write | Simple and correct at this scale; one rule covers every write | Optimistic version columns, which need retry logic in every caller |
| Domain exceptions + one handler | Services stay free of HTTP; status codes are decided in one place | `HTTPException` raised from services |
| Refresh token in an `httpOnly` cookie, access token in `localStorage` | Short-lived access tokens limit the damage of XSS; the long-lived token is out of reach of scripts | Access token in memory only, which needs a refresh on every page load |
| Append-only history enforced by the database | No code path, or manual query, can rewrite what happened | Trusting the application not to update events |
| `event_type` is a string column, named by a Python `EventType` enum | Its vocabulary grows with each feature; a string costs no migration per value, the enum keeps code and the activity filter honest | A Postgres enum (a migration per value) |
| Sort as `sort` + `order` query params, `id` as tiebreak | Every column sorts both ways with one rule; stable paging | One enum value per column and direction (`oldest`/`newest`), which doubles with each column |
| Toasts from the `MutationCache`, by `meta.successMessage` | One place raises every confirmation; components only state the message | `toast()` calls in every `onSuccess` |
| Confirmation step inside the note dialog | Repeats the note before a hard-to-undo action, with no second modal | A separate confirm modal stacked on the note dialog |
| One `events` table for clubs, comments, role changes and requests | One append-only log: the activity log is a query, not a second log to keep in sync | A table per kind, or a separate audit log written alongside |
| Comments are `comment_posted` events | They are permanent and need exactly what an event has (who, when, text, club); the thread and the activity log read one table | A `comments` table plus an event per comment |
| A role change is an event about a user (`subject_user_id`, check constraint) | It belongs in the activity log but has no club | Leaving role changes out of the history |
| Offset paging everywhere, comments deduped by id | One paging scheme for every list; a comment posted mid-scroll can only repeat, and the dedupe hides that | Cursor paging for comments only |
| CSV rendered in the router, cells starting `= + - @` prefixed with `'`, UTF-8 BOM | CSV is a transport format; names are user input that Excel would run as formulas; Excel needs the BOM for non-ASCII | Rendering in the service; a CSV library |
| Wrong current password is 403 | A 401 would make the frontend refresh and sign the user out | 401, or 400 with a new exception type |
| One request engine; types are data (details model + approval roles) | A new type adds fields and steps, not a new workflow, routes or UI states | A table and workflow per request type |
| Club registration stays its own workflow | It creates the club and has per-document review, which no request has | Making registration a request type |
| `awaiting_role` stored on the request | The review queue becomes one indexed query; a check constraint keeps it consistent with the status | Computing the current step per row from approvals |
| Approval rows unique per `(request, round, step)` | The database refuses a second approval of a step; a new round after changes keeps old approvals on record | Status flags per step on the request |
| `allowed_actions` in the response | The UI never re-implements the rules; the same table that enforces them lists them | Mirroring the state machine in TypeScript |
| Booking range on the request row | The exclusion constraint's `WHERE status IN (...)` must read the request's status in the same row | A `bookings` table, whose status would need syncing with the request's |
| Exclusion constraint for double booking | The database guarantees it under any concurrency or code path | Check-then-insert in the service, which races |
| Room row lock before booking writes | Racing bookings queue instead of deadlocking on each other's constraint checks; the 20-way test proves one wins | Retrying on deadlock |
| Money in integer cents | Exact sums; no float rounding | `Numeric`/`Decimal`, which also works but complicates JSON and the frontend |
| Rooms seeded by their migration | Every environment needs them; no admin UI exists for rooms yet | Seeding rooms only in `seed-demo` |
