from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from packages.saas.config import settings

Base = declarative_base()


def get_engine(db_url: str | None = None):
    url = db_url or settings.db_url
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in url else None,
        )

    # Use pg8000 driver for PostgreSQL if plain postgresql:// is provided
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)

    return create_engine(url, pool_pre_ping=True)


def get_sessionmaker(engine=None):
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


_engine = get_engine()
_SessionLocal = get_sessionmaker(_engine)


def init_db(engine=None):
    eng = engine or _engine
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        yield db
    finally:
        db.close()
