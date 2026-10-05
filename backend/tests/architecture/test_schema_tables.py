"""E1-S1 AC1: alembic upgrade head on an empty file creates all nine tables."""
from pathlib import Path

import pytest
from sqlalchemy import inspect

from telemed.repository.database import create_db_engine
from tests.conftest import migrate

EXPECTED = {
    "users",
    "patient_profiles",
    "patient_profile_versions",
    "doctor_profiles",
    "availability_templates",
    "slots",
    "appointments",
    "appointment_events",
    "consultation_notes",
}


@pytest.mark.ac("AC-E1-S1-1")
def test_upgrade_head_creates_all_tables(tmp_path: Path) -> None:
    path = tmp_path / "empty.db"
    migrate(path)
    engine = create_db_engine(str(path))
    try:
        assert EXPECTED <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
