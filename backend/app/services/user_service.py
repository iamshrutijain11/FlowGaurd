from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, data: RegisterRequest) -> User:
    if get_user_by_email(db, data.email):
        raise AppError("EMAIL_ALREADY_REGISTERED", "An account with this email already exists.", 409)
    user = User(
        name=data.name.strip(),
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        preferred_language=data.preferred_language,
    )
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise AppError("INVALID_CREDENTIALS", "Incorrect email or password.", 401)
    return user
