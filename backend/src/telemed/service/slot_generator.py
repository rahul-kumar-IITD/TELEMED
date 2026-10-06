"""Zone-aware, idempotent expansion of weekly availability templates into UTC slots."""
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from telemed.config.clock import Clock
from telemed.repository import doctors_repo, slots_repo
from telemed.repository.doctors_repo import TemplateRow
from telemed.service.unit_of_work import UnitOfWork
from telemed.types.ids import UserId

WINDOW = timedelta(days=14)


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _local_to_utc(day: date, minute_of_day: int, zone: ZoneInfo) -> datetime | None:
    """Wall-clock to UTC. DST-gap times return None; ambiguous times use the first occurrence."""
    wall = datetime.combine(day, time()) + timedelta(minutes=minute_of_day)
    utc = wall.replace(tzinfo=zone).astimezone(UTC)  # fold=0: first occurrence
    if utc.astimezone(zone).replace(tzinfo=None) != wall:
        return None
    return utc


def expand_template(
    template: TemplateRow, now: datetime, zone: ZoneInfo
) -> Iterator[tuple[datetime, datetime]]:
    """Yield (start_utc, end_utc) for every slot with now < start < now + 14 days."""
    first_day = now.astimezone(zone).date()
    last_day = (now + WINDOW).astimezone(zone).date()
    opens, closes = _minutes(template.start_time), _minutes(template.end_time)
    length = template.slot_length_minutes
    for offset in range((last_day - first_day).days + 1):
        day = first_day + timedelta(days=offset)
        if day.weekday() != template.weekday:
            continue
        for begin in range(opens, closes - length + 1, length):
            start = _local_to_utc(day, begin, zone)
            if start is not None and now < start < now + WINDOW:
                yield start, start + timedelta(minutes=length)


class SlotGenerator:
    def __init__(self, uow: UnitOfWork, clock: Clock, timezone_name: str) -> None:
        self._uow = uow
        self._clock = clock
        self._zone = ZoneInfo(timezone_name)

    def generate(self) -> int:
        """Top up the rolling window for all active doctors; returns the number of new slots."""
        now = self._clock.now()
        with self._uow.transaction() as session:
            templates = doctors_repo.list_active_doctor_templates(session)
            return self._insert(session, templates, now)

    def generate_for(self, session: Session, doctor_id: UserId) -> int:
        """Top up one doctor's window inside the caller's transaction (used by onboarding)."""
        templates = doctors_repo.list_doctor_templates(session, doctor_id)
        return self._insert(session, templates, self._clock.now())

    def _insert(self, session: Session, templates: list[TemplateRow], now: datetime) -> int:
        created = 0
        for template in templates:
            for start, end in expand_template(template, now, self._zone):
                if slots_repo.insert_available_if_absent(
                    session, template.doctor_id, start, end, now
                ):
                    created += 1
        return created
