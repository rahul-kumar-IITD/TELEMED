"""E1-S1 AC2: UPDATE and DELETE on append-only tables are rejected and rows unchanged."""
import sqlite3
from pathlib import Path

import pytest

from telemed.repository.triggers import APPEND_ONLY_TABLES

NOW = "2026-10-05 10:00:00.000000"

SEED = [
    "INSERT INTO users VALUES (1,'p@example.test','$argon2id$x','PATIENT',1,"
    f"'{NOW}','{NOW}')",
    "INSERT INTO users VALUES (2,'d@example.test','$argon2id$x','DOCTOR',1,"
    f"'{NOW}','{NOW}')",
    f"INSERT INTO patient_profiles VALUES (1,'{NOW}')",
    f"INSERT INTO doctor_profiles VALUES (2,'Dr D','Cardiology','[\"en\"]',50000,'{NOW}','{NOW}')",
    "INSERT INTO slots (slot_id,doctor_id,start_time,end_time,status,created_at,updated_at) "
    "VALUES (1,2,'2026-10-06 03:00:00.000000','2026-10-06 03:30:00.000000','BOOKED',"
    f"'{NOW}','{NOW}')",
    "INSERT INTO appointments (appointment_id,patient_id,doctor_id,slot_id,status,fee_minor,"
    f"created_at,updated_at) VALUES (1,1,2,1,'BOOKED',50000,'{NOW}','{NOW}')",
]

ROWS = {
    "patient_profile_versions": (
        "INSERT INTO patient_profile_versions (version_id,patient_id,version_number,full_name,"
        "age,gender,phone,changed_by_user_id,created_at) "
        f"VALUES (1,1,1,'Test Patient',30,'FEMALE','555',1,'{NOW}')",
        "full_name",
    ),
    "appointment_events": (
        "INSERT INTO appointment_events (event_id,appointment_id,event_type,from_status,"
        "to_status,actor_user_id,actor_role,created_at) "
        f"VALUES (1,1,'BOOKED',NULL,'BOOKED',1,'PATIENT','{NOW}')",
        "to_status",
    ),
    "consultation_notes": (
        "INSERT INTO consultation_notes (note_id,appointment_id,author_id,text,created_at) "
        f"VALUES (1,1,2,'synthetic note','{NOW}')",
        "text",
    ),
}


@pytest.fixture
def conn(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, isolation_level=None)
    for statement in SEED:
        connection.execute(statement)
    for insert, _ in ROWS.values():
        connection.execute(insert)
    return connection


@pytest.mark.ac("AC-E1-S1-2")
@pytest.mark.parametrize("table", sorted(APPEND_ONLY_TABLES))
@pytest.mark.nfr("NFR-02")
def test_update_and_delete_rejected(conn: sqlite3.Connection, table: str) -> None:
    column = ROWS[table][1]
    before = conn.execute(f"SELECT * FROM {table}").fetchall()
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute(f"UPDATE {table} SET {column} = 'changed'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute(f"DELETE FROM {table}")
    assert conn.execute(f"SELECT * FROM {table}").fetchall() == before
    assert len(before) == 1
