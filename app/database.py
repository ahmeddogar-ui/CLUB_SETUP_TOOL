from sqlalchemy import create_engine
from typing import Annotated, TypeAlias
from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

DbSession: TypeAlias = Annotated[Session, Depends(get_db)]
