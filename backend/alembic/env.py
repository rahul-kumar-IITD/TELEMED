"""Alembic environment bound to the telemed repository metadata."""
import os

from alembic import context
from sqlalchemy import create_engine

from telemed.repository.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return f"sqlite:///{os.environ.get('DATABASE_PATH', './telemed.db')}"


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
