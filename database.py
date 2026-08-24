from dotenv import load_dotenv
from sqlalchemy import create_engine
import os 
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]
