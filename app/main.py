from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.database import DbSession
from app.exceptions import Conflict, DomainError, Forbidden, NotFound, Unauthorized
from app.routers.auth import router as auth_router
from app.routers.clubs import router as clubs_router
from app.routers.requirements import router as requirements_router

# Where `npm run build` puts the React app. In development Vite serves it instead.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(
    docs_url="/api/docs" if settings.ENABLE_API_DOCS else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_API_DOCS else None,
    redoc_url=None,
)


async def revalidate_html_pages(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Browsers must re-check index.html on every load: after a deploy, a cached
    copy would point at hashed asset files that no longer exist. The hashed
    assets themselves never change, so they keep normal caching."""
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.middleware("http")(revalidate_html_pages)

STATUS_FOR_ERROR: dict[type[DomainError], int] = {
    NotFound: 404,
    Forbidden: 403,
    Conflict: 409,
    Unauthorized: 401,
}


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    status_code = STATUS_FOR_ERROR[type(error)]
    # RFC 6750: a 401 tells the client which auth scheme to use.
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code, content={"detail": str(error)}, headers=headers
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dbhealth")
def db_health(db: DbSession) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})


# Everything the React app calls lives under /api, so the same paths work in
# development (through Vite's proxy) and in production (same origin).
api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(clubs_router)
api.include_router(requirements_router)
app.include_router(api)

# Checked only after every route above: built files as they are, index.html for
# page navigations to client-side routes (/clubs/3), and 404 for anything else.
if FRONTEND_DIST.is_dir():
    app.frontend("/", directory=FRONTEND_DIST, fallback="index.html")
