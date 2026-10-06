"""Engine construction and per-connection pragmas."""
from typing import Any

from sqlalchemy import Engine, create_engine, event

MIN_BUSY_TIMEOUT_MS = 5000


def apply_pragmas(dbapi_connection: Any, busy_timeout_ms: int) -> None:
    """Set WAL, busy timeout (floored at 5000 ms), foreign keys and synchronous mode."""
    timeout = max(int(busy_timeout_ms), MIN_BUSY_TIMEOUT_MS)
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={timeout}")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


def create_db_engine(database_path: str, busy_timeout_ms: int = 10000) -> Engine:
    """Create a SQLite engine whose every new connection gets the standard pragmas."""
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"isolation_level": None, "timeout": MIN_BUSY_TIMEOUT_MS / 1000},
    )

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        apply_pragmas(dbapi_connection, busy_timeout_ms)

    return engine
