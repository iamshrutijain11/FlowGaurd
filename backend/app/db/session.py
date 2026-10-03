from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

_url = settings.DATABASE_URL
if _url.startswith("sqlite"):
    _kwargs: dict = {"connect_args": {"check_same_thread": False}}
    if _url in ("sqlite://", "sqlite:///:memory:"):
        _kwargs["poolclass"] = StaticPool  # single shared in-memory DB (tests)
    engine = create_engine(_url, **_kwargs)
else:
    engine = create_engine(_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
