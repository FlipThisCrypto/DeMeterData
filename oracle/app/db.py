# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy engine + Session factory.

All FastAPI routes obtain a Session via the `get_db` dependency. Schema
is created on app startup (see main.py); for migrations later we'll
swap in Alembic.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def engine():
    global _engine
    if _engine is None:
        url = settings().db_url
        # SQLite + the default check_same_thread guard makes FastAPI's
        # threadpool unhappy — turn it off for SQLite specifically.
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, future=True)
    return _engine


def session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine(), autoflush=False, autocommit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — one DB session per request, always closed."""
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Called once on app startup. Idempotent."""
    Base.metadata.create_all(engine())


def reset_for_tests() -> None:
    """Tests using a different DB URL should call this to reset the engine."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
