# Stage 1: build the React frontend. Only frontend/dist is kept.
FROM node:26-slim AS frontend
WORKDIR /frontend
# Lockfiles first so `npm ci` is cached until dependencies change.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python app, which also serves the built frontend.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /uvx /bin/
WORKDIR /app
# Lockfiles first so `uv sync` is cached until dependencies change.
# package = false in pyproject.toml, so there is no project to install afterwards.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini ./
COPY --from=frontend /frontend/dist frontend/dist

# Files stay root-owned, so the app cannot modify its own code.
RUN useradd appuser
USER appuser
ENV PATH="/app/.venv/bin:$PATH"

# Migrations run on every start (a no-op when up to date); Render sets PORT.
# Render terminates TLS in front of the app, so trust its X-Forwarded-* headers
# for the real scheme and client IP.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --forwarded-allow-ips='*'"]
