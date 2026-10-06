"""E3-S4: concurrent reschedules to one target slot have exactly one winner."""
# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.integration.conftest import (  # noqa: F401 - fixtures re-exported for this package
    NOW,
    Doctor,
    admin,
    app,
    appt_row,
    book_at,
    client,
    doctor,
    events,
    payment,
    provider_tz,
    register,
    slot_ids,
    slot_status,
)


@pytest.mark.ac("E3-S4-AC3")
def test_ten_concurrent_reschedules_one_winner(
    client: TestClient, engine: Engine, doctor: Doctor
) -> None:
    target = slot_ids(engine, doctor[0], 12)[-1]
    patients = [register(client, f"r{i}@example.test") for i in range(10)]
    booked = [
        book_at(client, engine, doctor[0], p, NOW + timedelta(hours=5, minutes=i))
        for i, p in enumerate(patients)
    ]
    barrier = Barrier(10)

    def attempt(index: int) -> int:
        barrier.wait()
        return client.post(
            f"/api/appointments/{booked[index][0]}/reschedule", headers=patients[index],
            json={"new_slot_id": target},
        ).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(attempt, range(10)))
    assert sorted(codes) == [200] + [409] * 9
    winner = codes.index(200)
    assert slot_status(engine, target) == "BOOKED"
    for index, (appt, old) in enumerate(booked):
        won = index == winner
        assert appt_row(engine, appt).slot_id == (target if won else old)
        assert slot_status(engine, old) == ("AVAILABLE" if won else "BOOKED")
        assert len(events(engine, appt)) == (2 if won else 1)
