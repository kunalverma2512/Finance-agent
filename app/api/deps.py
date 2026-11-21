from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.integrations.gemini import build_llm
from app.integrations.llm import LLMClient
from app.models import User

bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if creds is None:
        raise UnauthorizedError("Authentication required", code="NOT_AUTHENTICATED")
    payload = decode_access_token(creds.credentials)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid authentication token", code="INVALID_TOKEN") from exc
    user = db.get(User, user_id)
    if not user or not user.is_active or user.token_version != payload["tv"]:
        raise UnauthorizedError("Session is no longer valid", code="INVALID_TOKEN")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_llm(request: Request) -> LLMClient | None:
    """Overridable in tests via app.state.llm_override."""
    override = getattr(request.app.state, "llm_override", "unset")
    if override != "unset":
        return override
    if not hasattr(request.app.state, "llm"):
        request.app.state.llm = build_llm(get_settings())
    return request.app.state.llm


LLM = Annotated[LLMClient | None, Depends(get_llm)]
