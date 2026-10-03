import uuid
from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError
from app.utils.time import utcnow


def _pw_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = utcnow()
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise AppError("TOKEN_EXPIRED", "Your session has expired. Please log in again.", 401)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppError("INVALID_TOKEN", "Invalid authentication token.", 401)
