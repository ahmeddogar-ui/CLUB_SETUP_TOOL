from fastapi import FastAPI
from database import DbSession
from sqlalchemy import text

app = FastAPI()


@app.get("/health")
async def root():
    return {"message": "Hello World"}

@app.get("/dbhealth")
async def db_health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}