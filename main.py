from fastapi import Depends, FastAPI
from database import DbSession
from sqlalchemy import text
from fastapi import APIRouter, HTTPException, status
from database import DbSession
from models import User, UserRole
from auth.security import hash_password
from fastapi.security import OAuth2PasswordRequestForm
from auth.security import verify_password, create_access_token, get_current_user
from schemas import UserOut, UserRegisterRequest
from routers.clubs import router as clubs_router


app = FastAPI()

router = APIRouter()

@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: DbSession):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.club_lead,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: DbSession = None):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

#need to add logic that lets the admin reviewer log in - ie he will have a given email and if he logs in with the email his user role is admin
@app.get("/health")
async def root():
    return {"message": "Hello World"}

@app.get("/dbhealth")
async def db_health(db: DbSession):
    db.execute(text("SELECT 1"))
    return {"db": "ok"}

app.include_router(router)
app.include_router(clubs_router)