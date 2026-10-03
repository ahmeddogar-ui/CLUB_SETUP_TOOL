from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings
from app.database import DbSession
from sqlalchemy import text
from app.routers.clubs import router as clubs_router
from app.routers.auth import router as auth_router
from app.routers.requirements import router as requirements_router
from app.routers.web import router as web_router

app = FastAPI()

# Signed (not encrypted) cookie session for the browser pages; the JSON API
# keeps using bearer JWTs and never touches it.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    same_site="lax",
    https_only=settings.SESSION_HTTPS_ONLY,
)


#need to add logic that lets the admin reviewer log in - ie he will have a given email and if he logs in with the email his user role is admin
@app.get("/health")
async def root():
    return {"message": "Hello World"}

@app.get("/dbhealth")
async def db_health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}

app.include_router(clubs_router)
app.include_router(auth_router)
app.include_router(requirements_router)
app.include_router(web_router)