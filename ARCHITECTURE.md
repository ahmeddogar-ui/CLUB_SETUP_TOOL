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
| `routers/` | HTTP only: parse the request, call one service function, return a schema. `auth.py`, `clubs.py`, `requirements.py` |
| `services/` | Business rules for auth, clubs and requirements. No FastAPI imports |
| `transitions.py` | The club state machine: which status changes are allowed, by whom, and their guards |
| `models.py` | SQLAlchemy tables, enums and constraints |
| `schemas.py` | Request/response shapes and every input limit (named constants) |
| `exceptions.py` | `NotFound`, `Forbidden`, `Conflict`, `Unauthorized`, raised by services |
| `core/config.py` | Settings, read once from the environment or `.env` |
| `core/security.py` | Password hashing, JWTs, and the `get_current_user` / `require_role` dependencies |
| `seed.py`, `cli.py` | `make-admin` and `seed-demo` operator commands |

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
- **History is permanent.** `club_events` is append-only: a database trigger
  rejects `UPDATE` and `DELETE`, and its foreign key to `clubs` is `RESTRICT`,
  so a club with history can't be deleted either.
- **Validate at the edge.** Pydantic schemas trim and bound every string
  (`schemas.py`); the database adds enums, unique constraints, a lowercase-email
  check and foreign keys. Services trust their input.

### Data model

`users` (role `admin` or `club_lead`) → `clubs` (one submitter, one status) →
`requirements` (six per club, created with the club: four document links and
two checklist items) and `club_events` (one row per action, newest first via
`idx_events_club_time`). `refresh_tokens` stores SHA-256 hashes of login tokens.
`idx_clubs_status_updated` serves lists filtered by status and sorted by last
update (the review queue and the admin's status tabs).

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
`status` (repeatable), `sort` (`oldest`/`newest`), `q` (case-insensitive name
search; `%` and `_` match literally), `limit` (1–100, default 20) and `offset`.
Each item adds `owner_name`, `updated_at` and `documents_provided` /
`documents_total` to the club. A page costs three queries whatever its size:
the items (owner join plus correlated document counts), the filtered `total`,
and one `GROUP BY status` for `status_counts`, which covers every club the
user can see and ignores the filters. A document counts as provided while it
is `submitted` or `approved` (`DOCUMENT_PROVIDED_STATUSES`, shared with the
submit guard). A club's `updated_at` moves on every status change, edit and
new document link; reviewing a requirement doesn't move it, so the review
queue's "waiting" time is the time since the last status change.

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
- Everyone who signs up is a club lead. Admins are made with
  `python -m app.cli make-admin <email>`.

## Frontend (`frontend/`)

React 19 + TypeScript + Vite + Tailwind, built on the TailAdmin template's UI
primitives (`src/components/ui`, MIT, see `frontend/LICENSE.md`).

| Path | Role |
| --- | --- |
| `src/main.tsx` | Entry point: query client, router, theme, auth providers |
| `src/App.tsx` | The only route table |
| `src/components/layout/app-layout/` | Sidebar (two links) and header around every signed-in page |
| `src/components/shared/` | `RequireAuth`, `RequireAdmin`, page title, logo |
| `src/pages/main/clubs/` | Every club screen and its dialogs |
| `src/pages/others/auth/` | Sign in and sign up |
| `src/lib/api.ts` | `apiFetch()`, the only way to call the backend |
| `src/lib/types.ts` | The backend's JSON shapes, mirroring `app/schemas.py` |
| `src/lib/limits.ts` | Input limits, mirroring `app/schemas.py` |
| `src/contexts/` | Auth (current user, sign in/out) and theme (light/dark) |

### Data fetching

TanStack Query handles all server data: `useQuery` to read, `useMutation` to
change. Query keys are `["me", token]`, `["clubs", "list", filters]` (every
club list: status, search, sort and page; built by `clubPageQuery`),
`["clubs", id]`, `["clubs", id, "requirements"]` and `["clubs", id, "events"]`.
Every club change goes through `useClubMutation`, which invalidates `["clubs"]`
so all club data refetches. 4xx errors are not retried; 5xx and network errors
retry up to three times.

### Sessions and 401s

All 401 handling is in two places:

1. `apiFetch`: a 401 on a request that carried a token means the access token
   expired. It calls `/api/auth/refresh` once and retries. If the refresh fails
   too, it clears the token and dispatches a `session-expired` window event.
2. `AuthProvider`: listens for that event and signs out locally, clearing the
   token and the query cache. `RequireAuth` then sends the user to `/signin`.

An event is used because `apiFetch` is a plain module with no access to React
state; the auth context owns sign-out.

### Screens

| URL | Who | Page |
| --- | --- | --- |
| `/signin`, `/signup` | signed out | Sign in; register as a club lead |
| `/` | everyone | `clubs-page.tsx`: a lead's own clubs, or every club for an admin with status counts, status tabs and a name search. Status, search and page are in the URL (`?status=&q=&page=`) |
| `/clubs/new` | club leads | `new-club-page.tsx` |
| `/clubs/:clubId` | owner or admin | `club-detail-page.tsx`: details, requirements, history, actions |
| `/review` | admins | `review-queue-page.tsx`: submitted and under-review clubs, oldest first, with how long each has waited |

The backend enforces every rule; the UI only hides buttons that would be
refused, and shows the backend's message when something is.

Every list pages through 20 clubs at a time, and every empty list says why
and offers a next step (create a club, clear the filters, go to the first page).

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
| `event_type` is a string, not an enum | Its vocabulary is still growing; each new enum value would cost a migration | A Postgres enum |
