from fastapi import APIRouter, Depends

from app.api.deps import DB, CurrentUser
from app.core.rate_limit import auth_rate_limit
from app.schemas.auth import LoginIn, ProfileUpdate, RegisterIn, TokenOut, UserOut
from app.schemas.common import Message
from app.services.auth import AuthService

router = APIRouter()


@router.post("/auth/register", response_model=UserOut, status_code=201,
             dependencies=[Depends(auth_rate_limit)])
def register(data: RegisterIn, db: DB):
    return AuthService(db).register(data)


@router.post("/auth/login", response_model=TokenOut, dependencies=[Depends(auth_rate_limit)])
def login(data: LoginIn, db: DB):
    return AuthService(db).login(data)


@router.post("/auth/logout", response_model=Message)
def logout(user: CurrentUser, db: DB):
    AuthService(db).logout(user)
    return Message(message="Logged out; all existing tokens are now invalid")


@router.get("/profile", response_model=UserOut)
def profile(user: CurrentUser):
    return user


@router.patch("/profile", response_model=UserOut)
def update_profile(data: ProfileUpdate, user: CurrentUser, db: DB):
    return AuthService(db).update_profile(user, data)
