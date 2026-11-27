# Club Setup Tool

[![CI](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml)

Club administration for UTM student clubs. A club lead registers a club and
links its paperwork; an admin reviews each document and approves the club.
Once approved, the club files requests (funding with line items, room
bookings) that go through each request type's approval steps. Every action is
recorded in one permanent history that admins can search.

## Features

- **Club registration:** create a club, link its four documents, submit; the
  admin starts a review, approves or rejects each requirement, then approves,
  rejects or asks for changes. A confirmation step guards reject and request
  changes.
- **Requests for approved clubs**, one engine for every type:
  - **Funding:** budget line items with a live total; approved by an admin,
    then a finance approver.
  - **Room booking:** a room and a time range; approved by an admin. The
    database refuses double bookings, and the UI says which room is taken.
  - Draft → submitted → in review → approved / rejected / changes requested,
    with each approval step recorded (who, when, note), and cancel.
- **Review queue:** clubs and requests waiting for you, longest waiting first.
- **Discussion:** a comment thread on every club between its lead and admins.
- **Activity log (admins):** every action in the app, filterable by person,
  club, action and date.
- **Users (admins):** search users, change roles (admin, club lead, finance
  approver). Admins can't remove their own admin role.
- **Admin club list:** status summary, status tabs, search, sortable columns,
  CSV export of the current view.
- **Profile:** change your name and password.
- Toast confirmations, loading skeletons, page titles, and layouts that work
  on a phone.

## Screenshots
From the demo data (`seed-demo`), in the order a visitor, an admin, a finance
approver and a club lead meet them.

### Visitor

**Landing**

![Landing](docs/screenshots/01-visitor-landing.png)

**Sign in**

![Sign in](docs/screenshots/02-visitor-sign-in.png)

**Sign up**

![Sign up](docs/screenshots/03-visitor-sign-up.png)

### Admin

**All clubs**

![All clubs](docs/screenshots/04-admin-all-clubs.png)

**All clubs sorted by name**

![All clubs sorted by name](docs/screenshots/05-admin-all-clubs-sorted-by-name.png)

**Club detail under review with discussion**

![Club detail under review with discussion](docs/screenshots/06-admin-club-detail-under-review-with-discussion.png)

**Reject confirmation step**

![Reject confirmation step](docs/screenshots/07-admin-reject-confirmation-step.png)

**Club requests tab**

![Club requests tab](docs/screenshots/08-admin-club-requests-tab.png)

**Review queue**

![Review queue](docs/screenshots/09-admin-review-queue.png)

**Booking request in review**

![Booking request in review](docs/screenshots/10-admin-booking-request-in-review.png)

**Users**

![Users](docs/screenshots/11-admin-users.png)

**Activity log**

![Activity log](docs/screenshots/12-admin-activity-log.png)

**Profile**

![Profile](docs/screenshots/13-admin-profile.png)

### Finance approver

**Review queue**

![Review queue](docs/screenshots/14-finance-review-queue.png)

**Funding request at finance step**

![Funding request at finance step](docs/screenshots/15-finance-funding-request-at-finance-step.png)

### Club lead

**My clubs**

![My clubs](docs/screenshots/16-lead-my-clubs.png)

**Approved club requests tab**

![Approved club requests tab](docs/screenshots/17-lead-approved-club-requests-tab.png)

**New funding request**

![New funding request](docs/screenshots/18-lead-new-funding-request.png)

**New room booking**

![New room booking](docs/screenshots/19-lead-new-room-booking.png)

**Club detail changes requested**

![Club detail changes requested](docs/screenshots/20-lead-club-detail-changes-requested.png)

### Phone

**All clubs mobile**

![All clubs mobile](docs/screenshots/21-admin-all-clubs-mobile.png)

**Request detail mobile**

![Request detail mobile](docs/screenshots/22-admin-request-detail-mobile.png)


## Tech stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Postgres 16, Argon2 password hashing, JWT access tokens with an httpOnly refresh cookie
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query, React Hook Form + Zod, built on TailAdmin's UI primitives
- **Tests:** pytest against a real Postgres, Vitest + Testing Library + MSW, Playwright
- **Tooling:** uv, ruff, mypy, ESLint/oxlint, Prettier, GitHub Actions
- **Deployment:** one Docker image (Render), Postgres on Neon

[ARCHITECTURE.md](ARCHITECTURE.md) explains how the pieces fit together and why.

## Local setup

You need Postgres 16 running locally, [uv](https://docs.astral.sh/uv/) and
Node (the version in `frontend/.nvmrc`).

```sh
cp .env.example .env              # then check DATABASE_URL and set SECRET_KEY
createdb club_setup_tool
uv sync
uv run alembic upgrade head       # create the tables
uv run python -m app.cli seed-demo
cd frontend && npm ci
```

`seed-demo` creates an admin, a finance approver, four club leads, sixteen
clubs across every status, conversations on some of them, and funding and room
booking requests in every status. The migrations add five rooms. Sign in as
any of these (password `demo-password`):

| Email | Role | Has |
| --- | --- | --- |
| `demo-admin@example.com` | admin | Every club and request; clubs and requests waiting in the review queue |
| `demo-finance@example.com` | finance approver | Funding requests; one waiting for the finance step |
| `demo-lead@example.com` | club lead | Five clubs in different statuses; Robotics Club (approved) has requests |

Admins change roles on the Users page. To make the first admin:
`uv run python -m app.cli make-admin their@email.com`.

## Running the app

Development, with hot reload (two terminals):

```sh
uv run uvicorn app.main:app --reload     # API on http://localhost:8000
cd frontend && npm run dev               # app on http://localhost:5173
```

Production-like, one server: `cd frontend && npm run build`, then
`uv run uvicorn app.main:app` serves the app and the API on
http://localhost:8000.

Or with Docker, which runs the production image against its own Postgres:

```sh
docker compose up --build                # http://localhost:8000
docker compose exec app python -m app.cli seed-demo
```

## Running the tests

```sh
createdb club_setup_tool_test
createdb club_setup_tool_e2e_test
cd frontend && npx playwright install chromium && cd ..

make test        # backend, frontend and end-to-end: what CI runs
make lint        # every static check CI runs
```

[TESTING.md](TESTING.md) covers the test layers, single-test commands and conventions.

## Deployment

The app deploys as one Docker web service on [Render](https://render.com),
with Postgres on [Neon](https://neon.tech). Both have free tiers.

1. **Database:** create a Neon project and copy its connection string
   (`postgresql://…?sslmode=require`).
2. **App:** in Render, choose **New → Blueprint** and connect this GitHub
   repository. Render reads `render.yaml`, which defines the service,
   generates `SECRET_KEY` and sets `SESSION_HTTPS_ONLY=true`.
3. When Render asks for `DATABASE_URL`, paste the Neon connection string.
4. Deploy. Each start runs `alembic upgrade head` before the server, so the
   tables are created on the first deploy. Render checks `/health`.
5. **Demo data (optional):** Render's free plan has no shell, so seed from your
   own machine against the Neon database:
   `DATABASE_URL='<neon connection string>' uv run python -m app.cli seed-demo`.
   The demo password is in this README, so anyone can then sign in to your
   deployment as the demo admin. That suits a public demo; skip this step otherwise.

On the free plan the service sleeps after 15 minutes without traffic, so the
first request after that takes about a minute.

## Environment variables

| Name | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | yes | | Postgres connection string. `postgres://` is accepted and converted |
| `SECRET_KEY` | yes | | Signs JWTs; at least 32 characters. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SESSION_HTTPS_ONLY` | no | `false` | Marks the refresh cookie `Secure`. Must be `true` in production |
| `ENABLE_API_DOCS` | no | `false` | Serves interactive API docs at `/api/docs` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Lifetime of an access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no | `14` | Lifetime of a login (refresh token) |
| `ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `PORT` | no | `8000` | Port the Docker image listens on (Render sets it) |
| `TEST_DATABASE_URL` | tests | `postgresql://localhost:5432/club_setup_tool_test` (via `make`) | Disposable database for pytest; its name must contain `test` |
| `E2E_DATABASE_URL` | tests | `postgresql://localhost:5432/club_setup_tool_e2e_test` | Database for the Playwright run |
| `API_URL` | no | `http://localhost:8000` | Where Vite's dev server proxies `/api` |

## Known trade-offs

Deliberate simplifications for v1, each worth revisiting before real use:

- **No login rate limiting.** Repeated wrong passwords are never slowed down.
  Add rate limiting at the proxy or on `/api/auth/login`.
- **No refresh-token rotation.** A refresh token stays valid for its 14 days
  unless that session logs out, so a stolen cookie keeps working until then.
  Rotation would also need the frontend to share one in-flight refresh.
- **Access token in `localStorage`.** Any XSS bug could read it. It expires
  after 30 minutes, and the long-lived refresh token is in an httpOnly cookie
  that scripts can't read. An access token can't be revoked before it expires.
- **Simple search.** Club and user search is a substring match (`ILIKE`),
  which scans the table; fine for thousands of rows. Beyond that, add a
  trigram index.
- **No email notifications.** Leads and approvers see what waits for them in
  the app (review queue, statuses, discussion) but aren't emailed.
- **Rooms have no admin screen.** The migration seeds them; changing them is a
  database task for now.
