# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy engine + Session factory.

All FastAPI routes obtain a Session via the `get_db` dependency. Schema
is created on app startup (see main.py); for migrations later we'll
swap in Alembic.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

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


def _sqlite_path_from_url(url: str) -> Path | None:
    """Return the on-disk SQLite path from a sqlite:/// URL, or None
    if the URL isn't sqlite-on-disk."""
    if not url.startswith("sqlite:///"):
        return None
    raw = url.replace("sqlite:///", "", 1)
    if raw in ("", ":memory:"):
        return None
    return Path(raw)


def _restrict_db_file_perms(db_path: Path) -> None:
    """Make the SQLite file owner-readable-only (0600).

    The DB stores per-Tree HMAC ``signing_key_hex`` in plaintext. On a
    multi-user POSIX host, default umask would leave it group/other-
    readable. We tighten to 0600 every startup; the chmod is idempotent
    and survives DB recreates.

    On Windows ``os.chmod`` only flips the read-only bit — it does
    NOT translate to a real ACL change. NTFS inherits ACLs from the
    parent directory, so the real protection on Windows is "don't put
    the oracle data dir somewhere group-readable" (e.g. keep it under
    your user profile). We log a one-line note on Windows so the
    operator knows the chmod was a no-op there.
    """
    try:
        os.chmod(db_path, 0o600)
    except OSError as e:
        # Don't crash startup if the FS doesn't support chmod (e.g.
        # FAT32 on a removable drive). Log loudly so the operator
        # knows the DB is not file-perm-protected.
        print(f"[oracle.db] WARN: could not chmod {db_path} to 0600: {e}",
              file=sys.stderr)
        return
    if sys.platform == "win32":
        print(f"[oracle.db] note: chmod 0600 on Windows only sets the "
              f"read-only bit. DB at {db_path} is protected by its "
              f"directory's NTFS ACL. Keep oracle/data under your user "
              f"profile.", file=sys.stderr)


def create_all() -> None:
    """Called once on app startup. Idempotent."""
    Base.metadata.create_all(engine())
    # Tighten file perms AFTER the DB file exists. SQLAlchemy creates
    # the file on first connection inside create_all().
    db_path = _sqlite_path_from_url(settings().db_url)
    if db_path is not None and db_path.exists():
        _restrict_db_file_perms(db_path)


def reset_for_tests() -> None:
    """Tests using a different DB URL should call this to reset the engine."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
