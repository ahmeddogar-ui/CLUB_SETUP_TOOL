from fastapi import FastAPI
from app.database import DbSession
from sqlalchemy import text
from fastapi import APIRouter
from app.database import DbSession
from app.routers.clubs import router as clubs_router
from app.routers.auth import router as auth_router

app = FastAPI()


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