"""Shared fixtures: a migrated temporary SQLite database per test."""
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from telemed.repository.database import create_db_engine

BACKEND = Path(__file__).resolve().parents[1]


def migrate(db_path: Path) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    migrate(path)
    return path


@pytest.fixture
def engine(db_path: Path) -> Iterator[Engine]:
    eng = create_db_engine(str(db_path))
    yield eng
    eng.dispose()
