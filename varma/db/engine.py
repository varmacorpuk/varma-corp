"""StoragePort: SQLite now (TEMPORARY), Postgres later via the same port."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from varma.config import DATA_DIR, get_settings
from varma.db.models import Base


class StoragePort(Protocol):
    """Replaceable persistence boundary (Document 14)."""

    def create_engine(self) -> Engine: ...

    def backend_name(self) -> str: ...

    def is_temporary_dev_store(self) -> bool: ...

    def persistence_note(self) -> str: ...


class SqliteStorage:
    """TEMPORARY DEVELOPMENT store. Not production. Not the Board Member's PC."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_settings().database_url

    def create_engine(self) -> Engine:
        if self._url.startswith("sqlite:///"):
            path = self._url.replace("sqlite:///", "", 1)
            if path not in {":memory:", ""} and not path.startswith("file:"):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {}
        if self._url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        engine = create_engine(self._url, connect_args=connect_args, future=True)
        if self._url.startswith("sqlite"):

            @event.listens_for(engine, "connect")
            def _fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
                dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine

    def backend_name(self) -> str:
        return "sqlite"

    def is_temporary_dev_store(self) -> bool:
        return True

    def persistence_note(self) -> str:
        return (
            "TEMPORARY SQLite file under data/. Practice paper-OPEN book "
            "data/varma_paper_open.db is tracked; data/varma.db stays gitignored. "
            "This box is DEVELOPMENT, not production runtime. Persistent org data "
            "must not live on the Board Member's Mac/Windows as source of truth. "
            "Postgres via docker-compose.yml replaces this through StoragePort "
            "when Docker is available. Backend is designed so it can later run "
            "24/7 off the Board Member's PC."
        )


class PostgresStorage:
    def __init__(self, url: str) -> None:
        self._url = url

    def create_engine(self) -> Engine:
        return create_engine(self._url, future=True, pool_pre_ping=True)

    def backend_name(self) -> str:
        return "postgres"

    def is_temporary_dev_store(self) -> bool:
        return False

    def persistence_note(self) -> str:
        return "PostgreSQL system of record (Document 14 / 18 Appendix A recommendation)."


def storage_from_url(url: str | None = None) -> StoragePort:
    u = url or get_settings().database_url
    if u.startswith("postgresql"):
        return PostgresStorage(u)
    return SqliteStorage(u)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(url: str | None = None, *, reset: bool = False) -> Engine:
    global _engine, _session_factory
    if reset:
        _engine = None
        _session_factory = None
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "README.txt").write_text(
            "TEMPORARY DEVELOPMENT database directory. Gitignored. "
            "Not a source of truth on a desktop. Replace via StoragePort/Postgres.\n",
            encoding="utf-8",
        )
        _engine = storage_from_url(url).create_engine()
    return _engine


def get_session_factory(url: str | None = None, *, reset: bool = False) -> sessionmaker[Session]:
    global _session_factory
    engine = get_engine(url, reset=reset)
    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return _session_factory


def init_db(url: str | None = None, *, reset: bool = False) -> Engine:
    engine = get_engine(url, reset=reset)
    Base.metadata.create_all(engine)
    return engine
