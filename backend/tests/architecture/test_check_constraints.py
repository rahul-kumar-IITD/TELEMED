"""E1-S1 AC5: invalid statuses are rejected by CHECK constraints."""
import sqlite3
from pathlib import Path

import pytest

NOW = "2026-10-05 10:00:00.000000"


@pytest.fixture
def conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(db_path, isolation_level=None)
    c.execute(
        f"INSERT INTO users VALUES (1,'p@example.test','$argon2id$x','PATIENT',1,'{NOW}','{NOW}')"
    )
    c.execute(
        f"INSERT INTO users VALUES (2,'d@example.test','$argon2id$x','DOCTOR',1,'{NOW}','{NOW}')"
    )
    c.execute(f"INSERT INTO patient_profiles VALUES (1,'{NOW}')")
    c.execute(
        "INSERT INTO doctor_profiles VALUES "
        f"(2,'Dr D','Cardiology','[\"en\"]',50000,'{NOW}','{NOW}')"
    )
    return c


def _slot(status: str) -> str:
    return (
        "INSERT INTO slots (doctor_id,start_time,end_time,status,created_at,updated_at) "
        "VALUES (2,'2026-10-06 03:00:00.000000','2026-10-06 03:30:00.000000',"
        f"'{status}','{NOW}','{NOW}')"
    )


@pytest.mark.ac("AC-E1-S1-5")
@pytest.mark.parametrize("status", ["AVAILABLE", "BOOKED", "BLOCKED"])
def test_slot_status_check(conn: sqlite3.Connection, status: str) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(_slot("HELD"))
    conn.execute(_slot(status))


@pytest.mark.ac("AC-E1-S1-5")
@pytest.mark.parametrize(
    "status",
    ["BOOKED", "CHECKED_IN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"],
)
def test_appointment_status_valid_and_invalid(conn: sqlite3.Connection, status: str) -> None:
    conn.execute(_slot("BOOKED"))
    insert = (
        "INSERT INTO appointments (patient_id,doctor_id,slot_id,status,fee_minor,created_at,"
        f"updated_at) VALUES (1,2,1,'STATUS',50000,'{NOW}','{NOW}')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(insert.replace("STATUS", "PENDING"))
    conn.execute(insert.replace("STATUS", status))
