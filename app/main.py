from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.database import DbSession
from app.exceptions import Conflict, DomainError, Forbidden, NotFound, Unauthorized
from app.frontend import FRONTEND_DIST, mount_frontend
from app.routers.auth import router as auth_router
from app.routers.clubs import router as clubs_router
from app.routers.requirements import router as requirements_router

app = FastAPI(
    docs_url="/api/docs" if settings.ENABLE_API_DOCS else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_API_DOCS else None,
    redoc_url=None,
)

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

# Last: it answers every path the routes above don't.
if FRONTEND_DIST.is_dir():
    mount_frontend(app, FRONTEND_DIST)
