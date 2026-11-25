# Club Setup Tool

[![CI](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml)

A web app for registering student clubs. A club lead creates a club, adds links
to its paperwork (constitution, exec list, budget, advisor form) and submits it.
An admin reviews each document, then approves the club, rejects it, or asks for
changes. Every step is recorded in the club's history.

<!-- Screenshot placeholder: add docs/screenshot.png and show it here with
![Club detail page](docs/screenshot.png) -->

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

`seed-demo` creates two demo accounts (password `demo-password` for both):

| Email | Role | Has |
| --- | --- | --- |
| `demo-admin@example.com` | admin | One club waiting in the review queue |
| `demo-lead@example.com` | club lead | Three clubs: drafting, submitted, approved |

To make any registered user an admin: `uv run python -m app.cli make-admin their@email.com`.

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
- **No list pagination.** The club list and review queue return every
  matching club; fine for a few hundred clubs.
