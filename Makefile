# Local defaults; override on the command line or in your shell.
# Database names must contain "test" (tests/conftest.py enforces it).
export TEST_DATABASE_URL ?= postgresql://localhost:5432/club_setup_tool_test
export E2E_DATABASE_URL ?= postgresql://localhost:5432/club_setup_tool_e2e_test

.PHONY: test test-fast test-backend test-frontend test-e2e coverage lint

## Everything CI runs as tests: backend, frontend, end-to-end.
test: test-backend test-frontend test-e2e

## The inner loop: backend and frontend tests, stop at first failure, no e2e.
test-fast:
	uv run pytest -q -x
	cd frontend && npm test -- --bail=1

test-backend:
	uv run pytest -q

test-frontend:
	cd frontend && npm test

test-e2e:
	cd frontend && npm run test:e2e

coverage:
	uv run pytest -q --cov --cov-report=html
	cd frontend && npm run test:coverage

## Every static check CI gates on.
lint:
	uv run ruff check app tests
	uv run mypy
	cd frontend && npm run format:check && npm run lint && npm run typecheck
