import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT from POST /api/v1/auth/login")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise AppError("NOT_AUTHENTICATED", "Authentication required.", 401)
    user_id: uuid.UUID = decode_access_token(creds.credentials)
    user = db.get(User, user_id)
    if not user:
        raise AppError("INVALID_TOKEN", "Invalid authentication token.", 401)
    return user
