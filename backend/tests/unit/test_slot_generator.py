"""E2-S1 AC1-AC4: zone-aware idempotent slot generation."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from telemed.repository.models import Slot
from telemed.service.slot_generator import SlotGenerator
from telemed.service.unit_of_work import UnitOfWork
from tests.conftest import FrozenClock
from tests.factories import add_doctor

MONDAY_MORNING = [(0, "09:00", "12:00", 30)]


def _generator(engine: Engine, clock: FrozenClock, zone: str = "UTC") -> SlotGenerator:
    return SlotGenerator(UnitOfWork(engine), clock, zone)


def _starts(engine: Engine) -> list[datetime]:
    with Session(engine) as session:
        return list(session.scalars(select(Slot.start_time).order_by(Slot.start_time)))


@pytest.mark.ac("AC-E2-S1-1")
def test_monday_template_yields_six_slots_per_monday(
    engine: Engine, frozen_clock: FrozenClock
) -> None:
    doctor = add_doctor(engine, "d1@example.test", MONDAY_MORNING)
    created = _generator(engine, frozen_clock).generate()
    starts = _starts(engine)
    assert created == 12  # Mondays 2026-10-12 and 2026-10-19, six each
    assert [s.date().isoformat() for s in starts[:6]] == ["2026-10-12"] * 6
    assert starts[0].hour == 9 and starts[5] == datetime(2026, 10, 12, 11, 30, tzinfo=UTC)
    with Session(engine) as session:
        rows = session.scalars(select(Slot)).all()
        assert {r.status for r in rows} == {"AVAILABLE"}
        assert {r.doctor_id for r in rows} == {doctor}
        assert rows[0].end_time - rows[0].start_time == timedelta(minutes=30)


@pytest.mark.ac("AC-E2-S1-2")
def test_window_is_exclusive_at_both_edges(engine: Engine, frozen_clock: FrozenClock) -> None:
    add_doctor(engine, "d1@example.test", [(i, "00:00", "23:00", 60) for i in range(7)])
    frozen_clock.advance(timedelta(hours=1))  # now = 01:00 on Tuesday 2026-10-06
    _generator(engine, frozen_clock).generate()
    starts = _starts(engine)
    now = frozen_clock.now()
    assert starts[0] == now + timedelta(hours=1)  # 02:00; the 01:00 slot (== now) excluded
    assert all(now < s < now + timedelta(days=14) for s in starts)
    # the slot at exactly now + 14d (Oct 20 01:00) is excluded; 00:00 is the last one
    assert starts[-1] == now + timedelta(days=14) - timedelta(hours=1)


@pytest.mark.ac("AC-E2-S1-2")
def test_slot_starting_exactly_now_or_at_fourteen_days_is_skipped(
    engine: Engine, frozen_clock: FrozenClock
) -> None:
    add_doctor(engine, "d1@example.test", [(1, "00:00", "01:00", 60)])  # Tuesday 00:00
    # now == Tue 2026-10-06 00:00: that slot (== now) and Oct 20 (== now + 14d) are excluded
    assert _generator(engine, frozen_clock).generate() == 1
    assert _starts(engine) == [datetime(2026, 10, 13, 0, 0, tzinfo=UTC)]
    frozen_clock.advance(timedelta(minutes=-1))  # Oct 6 00:00 is now inside, Oct 20 still out
    assert _generator(engine, frozen_clock).generate() == 1
    assert _starts(engine) == [
        datetime(2026, 10, 6, 0, 0, tzinfo=UTC),
        datetime(2026, 10, 13, 0, 0, tzinfo=UTC),
    ]


@pytest.mark.ac("AC-E2-S1-3")
def test_running_twice_creates_no_duplicates(engine: Engine, frozen_clock: FrozenClock) -> None:
    add_doctor(engine, "d1@example.test", MONDAY_MORNING)
    generator = _generator(engine, frozen_clock)
    assert generator.generate() == 12
    assert generator.generate() == 0
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Slot)) == 12
        duplicates = session.execute(
            text("SELECT 1 FROM slots GROUP BY doctor_id, start_time HAVING COUNT(*) > 1")
        ).all()
        assert duplicates == []


@pytest.mark.ac("AC-E2-S1-4")
def test_template_time_is_interpreted_in_provider_timezone(
    engine: Engine, frozen_clock: FrozenClock
) -> None:
    add_doctor(engine, "d1@example.test", MONDAY_MORNING)
    _generator(engine, frozen_clock, "Asia/Kolkata").generate()
    first = _starts(engine)[0]
    assert first == datetime(2026, 10, 12, 3, 30, tzinfo=UTC)
    assert first.utcoffset() == timedelta(0)


def test_inactive_doctor_gets_no_slots(engine: Engine, frozen_clock: FrozenClock) -> None:
    add_doctor(engine, "d1@example.test", MONDAY_MORNING, active=False)
    assert _generator(engine, frozen_clock).generate() == 0


def test_dst_gap_time_is_skipped_and_ambiguous_time_uses_first_occurrence(
    engine: Engine, frozen_clock: FrozenClock
) -> None:
    templates = [(i, "01:30", "02:30", 60) for i in range(7)]
    templates += [(i, "02:30", "03:30", 60) for i in range(7)]
    add_doctor(engine, "d1@example.test", templates)
    zone = "America/New_York"
    # DST ends 2026-11-01 (01:30 occurs twice) and starts 2027-03-14 (02:30 does not exist).
    frozen_clock.advance(timedelta(days=23))  # 2026-10-29 00:00 UTC
    _generator(engine, frozen_clock, zone).generate()
    nov1 = [s for s in _starts(engine) if s.date().isoformat() == "2026-11-01"]
    assert nov1 == [
        datetime(2026, 11, 1, 5, 30, tzinfo=UTC),  # 01:30 EDT, first occurrence
        datetime(2026, 11, 1, 7, 30, tzinfo=UTC),  # 02:30 EST
    ]
    frozen_clock.advance(timedelta(days=135))  # 2027-03-13 00:00 UTC
    _generator(engine, frozen_clock, zone).generate()
    mar14 = [s for s in _starts(engine) if s.date().isoformat() == "2027-03-14"]
    assert mar14 == [datetime(2027, 3, 14, 6, 30, tzinfo=UTC)]  # only 01:30 EST; 02:30 skipped
