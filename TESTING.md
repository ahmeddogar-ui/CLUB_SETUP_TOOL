# Testing

Three layers, each answering a different question:

| Layer | Tool | Where | What it proves | Runtime |
| --- | --- | --- | --- | --- |
| Backend | pytest + real Postgres | `tests/` | API rules: auth, ownership, the club state machine, history | ~4s |
| Frontend | Vitest + Testing Library + MSW | `frontend/src/**/*.test.ts(x)` | Pages behave correctly for each role and backend response | ~3s |
| End-to-end | Playwright | `frontend/e2e/` | The real stack works together on the main journey | ~15s |

Most tests live in the first two layers. E2E is kept to the one journey that would hurt most
if broken (a club going from draft to approved), because it is the slowest and hardest to debug.

## One-time setup

You need Postgres running locally, plus `uv` and Node (version in `frontend/.nvmrc`).

```sh
createdb club_setup_tool_test        # backend tests
createdb club_setup_tool_e2e_test    # end-to-end tests
uv sync
cd frontend && npm ci && npx playwright install chromium
```

Database names must contain `test`, and the backend tests refuse to run against the URL in
your `.env`. This keeps you from pointing them at real data. The Makefile defaults to
`postgresql://localhost:5432/<name>`. If yours differs, set `TEST_DATABASE_URL` and
`E2E_DATABASE_URL`.

## Running tests

| Goal | Command |
| --- | --- |
| Everything (what CI runs) | `make test` |
| Fast inner loop (no e2e, stop at first failure) | `make test-fast` |
| With coverage (HTML in `htmlcov/` and `frontend/coverage/`) | `make coverage` |
| All static checks | `make lint` |
| One backend file / test | `uv run pytest tests/test_clubs.py` / `uv run pytest -k "update and 409"` |
| Re-run only last failures | `uv run pytest --lf` |
| One frontend file | `cd frontend && npx vitest run src/lib/api.test.ts` |
| Frontend watch mode | `cd frontend && npm run test:watch` |
| E2E with the browser visible | `cd frontend && npx playwright test --headed` (or `--ui`) |

`make` exports `TEST_DATABASE_URL` for you. When you call `uv run pytest` directly, export
it yourself.

## Backend conventions

- **Real Postgres, real migrations.** The session fixture runs `alembic upgrade head`, so
  enums, constraints and the append-only trigger on `club_events` are the production ones.
  SQLite would hide exactly the bugs we care about.
- **Each test is rolled back.** `db` opens a transaction, and the app's own `commit()` calls
  only release a savepoint inside it. `test_harness.py` proves this keeps working.
- **Two ways to get a club.** Use `create_club(client, user)` when you want the real API
  path. Use `make_club(db, owner, status=...)` to place a club directly in some state, so a
  test about approval doesn't have to walk through submit first.
- **One file per feature area** (`test_auth.py`, `test_clubs.py`, `test_transitions.py`,
  ...). Test names describe behavior: `test_update_after_submission_is_409_and_changes_nothing`.
- **Check the database, not just the response**, for anything about data integrity: that
  nothing changed after a refused request, that exactly one event was written.
- **Order-of-checks tests are explicit.** For example, ownership is checked before status:
  a stranger gets 403, never a 409 that would reveal the club's state.

## Frontend conventions

- **Tests sit next to the code** (`club-detail-page.test.tsx` beside `club-detail-page.tsx`).
  Shared helpers are in `src/test/`.
- **Render the real app.** `renderApp(path, { signedInAs })` mounts `App` with the same
  providers as `main.tsx`, so route guards, layout and pages are exercised together.
- **Mock the network, not the code.** MSW answers `/api/...` requests. Each test declares
  the responses it depends on with `server.use(...)`. A request with no handler **fails the
  test**, even if the app swallowed the error, which is how "doesn't call the backend" tests
  are enforced. Build response bodies with `src/test/builders.ts` so they match
  `app/schemas.py`.
- **Query the way a user would**: `getByRole`, `getByLabelText`, then text. No test IDs
  and no class selectors.
- `src/components/ui` and `src/icons` (template primitives) are excluded from coverage.
  They are exercised through the pages.

## End-to-end conventions

- Playwright starts its own backend (port 8100) and Vite server (port 5174) against the
  e2e database, so it can run while your dev servers are up.
- Every run uses unique emails and names. Nothing is cleaned up, and nothing needs to be.
- There is no API for creating an admin, so `e2e/database.ts` promotes a user with `psql`,
  the same way an operator would.

## CI

`.github/workflows/ci.yml` runs four jobs in parallel on every PR and on pushes to `main`:

1. **Backend lint and types**: `ruff check` and `mypy`.
2. **Backend tests**: pytest with coverage against Postgres 16. Fails below 90% coverage.
3. **Frontend**: Prettier check, lint, `tsc`, Vitest with coverage floors (set in
   `vite.config.ts`), production build.
4. **End-to-end**: the Playwright journey. On failure, the HTML report and trace are
   uploaded as an artifact.

Coverage for both halves appears in each run's job summary. The thresholds are floors set
just under today's numbers, so treat a drop as a signal, not a target to game. Dependabot
opens grouped weekly PRs for test tooling, lint tooling and GitHub Actions.

## Known bugs

Mark a test that reproduces a known, unfixed bug with
`@pytest.mark.xfail(strict=True, reason="...")` (or `it.fails(...)` in Vitest) and link the
issue. `strict` means the test starts failing once someone fixes the bug, so the marker gets
removed. There are none at the moment.
