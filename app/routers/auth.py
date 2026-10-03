from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import get_current_user
from app.database import DbSession
from app.models import User
from app.schemas import UserOut, UserRegisterRequest
from app.services.auth import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: DbSession):
    return register_user(db, payload.name, payload.email, payload.password)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: DbSession = None):
    access_token = authenticate_user(db, form_data.username, form_data.password)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

