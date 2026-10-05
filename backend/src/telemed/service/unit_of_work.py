"""Transaction boundary exposed upward so the API never touches the repository layer."""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session


class UnitOfWork:
    """Opens write transactions (BEGIN IMMEDIATE) and read-only sessions on one engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """One short write transaction; commits on success, rolls back on any exception."""
        with Session(self._engine) as session:
            session.execute(text("BEGIN IMMEDIATE"))
            try:
                yield session
            except BaseException:
                session.rollback()
                raise
            session.commit()

    @contextmanager
    def read(self) -> Iterator[Session]:
        with Session(self._engine) as session:
            yield session

    def dispose(self) -> None:
        self._engine.dispose()
