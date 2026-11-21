from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginIn, ProfileUpdate, RegisterIn, TokenOut
from app.services.audit import audit

_DUMMY_HASH = hash_password("not-a-real-password-1")  # equalises timing for unknown emails


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, data: RegisterIn) -> User:
        if self.db.scalar(select(User.id).where(User.email == data.email)):
            raise ConflictError("Email is already registered", code="EMAIL_TAKEN")
        user = User(email=data.email, hashed_password=hash_password(data.password),
                    full_name=data.full_name.strip(), currency=data.currency)
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError as exc:  # concurrent registration race
            self.db.rollback()
            raise ConflictError("Email is already registered", code="EMAIL_TAKEN") from exc
        audit(self.db, user.id, "auth.register", "user", user.id)
        self.db.commit()
        return user

    def login(self, data: LoginIn) -> TokenOut:
        user = self.db.scalar(select(User).where(User.email == data.email.strip().lower()))
        ok = verify_password(data.password, user.hashed_password if user else _DUMMY_HASH)
        if not user or not ok or not user.is_active:
            raise UnauthorizedError("Invalid email or password", code="INVALID_CREDENTIALS")
        token, expires = create_access_token(user.id, user.token_version)
        audit(self.db, user.id, "auth.login", "user", user.id)
        self.db.commit()
        return TokenOut(access_token=token, expires_in=expires)

    def logout(self, user: User) -> None:
        user.token_version += 1  # invalidates every token issued so far
        audit(self.db, user.id, "auth.logout", "user", user.id)
        self.db.commit()

    def update_profile(self, user: User, data: ProfileUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.currency is not None:
            user.currency = data.currency
        self.db.commit()
        return user
