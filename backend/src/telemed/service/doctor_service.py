"""Admin onboarding of doctors: validate, then create everything in one transaction."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from telemed.config.clock import Clock
from telemed.repository import doctors_repo, slots_repo, users_repo
from telemed.service import security
from telemed.service.slot_generator import SlotGenerator
from telemed.service.unit_of_work import UnitOfWork
from telemed.types import domain
from telemed.types.domain import (
    DoctorOnboarding,
    DoctorSearch,
    DoctorSummary,
    OnboardedDoctor,
    StoredTemplate,
    TemplateSpec,
)
from telemed.types.enums import Role, SlotStatus
from telemed.types.errors import (
    FieldError,
    InputValidationException,
    InvalidSlotStateException,
    NotFoundException,
)
from telemed.types.ids import SlotId, UserId
from telemed.types.money import parse_fee

_logger = logging.getLogger("telemed.doctors")


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _template_errors(templates: tuple[TemplateSpec, ...]) -> list[FieldError]:
    errors: list[FieldError] = []
    windows: dict[int, list[tuple[int, int, int]]] = {}
    for index, spec in enumerate(templates):
        prefix = f"availability_templates[{index}]"
        start, end = _minutes(spec.start_time), _minutes(spec.end_time)
        length = spec.slot_length_minutes
        if end <= start:
            errors.append(FieldError(f"{prefix}.end_time", "end_time must be after start_time"))
        if length <= 0:
            errors.append(
                FieldError(f"{prefix}.slot_length_minutes", "slot length must be positive")
            )
        elif end > start and (end - start) % length != 0:
            errors.append(
                FieldError(f"{prefix}.slot_length_minutes", "slot length must divide the window")
            )
        if end > start:
            windows.setdefault(spec.weekday, []).append((start, end, index))
    for rows in windows.values():
        rows.sort()
        for (_, prev_end, _), (start, _, index) in zip(rows, rows[1:], strict=False):
            if start < prev_end:
                errors.append(
                    FieldError(
                        f"availability_templates[{index}].start_time",
                        "window overlaps another window on the same weekday",
                    )
                )
    return errors


def validate(details: DoctorOnboarding) -> Decimal:
    """Return the parsed fee or raise InputValidationException listing every problem."""
    errors: list[FieldError] = []
    fee = Decimal(0)
    try:
        fee = parse_fee(details.fee)
    except ValueError:
        errors.append(FieldError("fee", "fee must be a non-negative amount, max 2 decimals"))
    errors.extend(_template_errors(details.templates))
    if errors:
        raise InputValidationException(errors)
    return fee


_OPEN_WINDOW = timedelta(days=14)
_MAX_RANGE = timedelta(days=31)


class DoctorService:
    def __init__(self, uow: UnitOfWork, clock: Clock, slot_generator: SlotGenerator) -> None:
        self._uow = uow
        self._clock = clock
        self._slots = slot_generator

    def onboard(self, details: DoctorOnboarding, initial_password: str) -> OnboardedDoctor:
        """Create user, profile, templates and the first slots atomically (all or nothing)."""
        fee = validate(details)
        password_hash = security.hash_password(initial_password)  # before the write lock
        now = self._clock.now()
        with self._uow.transaction() as session:
            user = users_repo.insert_user(session, details.email, password_hash, Role.DOCTOR, now)
            doctor_id = user.user_id
            doctors_repo.insert_doctor_profile(
                session, doctor_id, details.full_name, details.specialty, details.languages,
                fee, now,
            )
            stored: list[StoredTemplate] = [
                doctors_repo.insert_template(session, doctor_id, spec, now)
                for spec in details.templates
            ]
            slots_created = self._slots.generate_for(session, doctor_id)
        _logger.info("doctor_onboarded", extra={"user_id": doctor_id})
        return OnboardedDoctor(
            doctor_id=doctor_id, email=user.email, full_name=details.full_name,
            specialty=details.specialty, languages=details.languages, fee=fee,
            templates=tuple(stored), slots_created=slots_created,
        )

    def my_slots(
        self, doctor_id: UserId, start: datetime | None, end: datetime | None
    ) -> list[domain.Slot]:
        """The caller's own slots in [start, end]; defaults now .. start + 14 days."""
        first = start if start is not None else self._clock.now()
        last = end if end is not None else first + _OPEN_WINDOW
        if last < first or last - first > _MAX_RANGE:
            raise InputValidationException(
                [FieldError("to", "to must not precede from and the range is at most 31 days")]
            )
        with self._uow.read() as session:
            return slots_repo.list_for_doctor(session, doctor_id, first, last)

    def block_slot(self, doctor_id: UserId, slot_id: SlotId) -> domain.Slot:
        return self._transition(doctor_id, slot_id, SlotStatus.AVAILABLE, SlotStatus.BLOCKED)

    def unblock_slot(self, doctor_id: UserId, slot_id: SlotId) -> domain.Slot:
        return self._transition(doctor_id, slot_id, SlotStatus.BLOCKED, SlotStatus.AVAILABLE)

    def _transition(
        self, doctor_id: UserId, slot_id: SlotId, expected: SlotStatus, new: SlotStatus
    ) -> domain.Slot:
        """One conditional UPDATE; on no-op, a foreign/absent slot is 404 and a wrong state 409."""
        with self._uow.transaction() as session:
            changed = slots_repo.transition(
                session, slot_id, doctor_id, expected.value, new.value, self._clock.now()
            )
            slot = slots_repo.get_owned(session, slot_id, doctor_id)
        if slot is None:
            raise NotFoundException()
        if not changed:
            raise InvalidSlotStateException()
        return slot

    def search(self, criteria: DoctorSearch) -> list[DoctorSummary]:
        if (
            criteria.available_from is not None
            and criteria.available_to is not None
            and criteria.available_to < criteria.available_from
        ):
            raise InputValidationException(
                [FieldError("available_to", "available_to must not precede available_from")]
            )
        now = self._clock.now()
        with self._uow.read() as session:
            return doctors_repo.search_active(session, criteria, now, now + _OPEN_WINDOW)

    def get_doctor(self, doctor_id: UserId) -> DoctorSummary:
        now = self._clock.now()
        with self._uow.read() as session:
            summary = doctors_repo.get_active_summary(session, doctor_id, now, now + _OPEN_WINDOW)
        if summary is None:
            raise NotFoundException()
        return summary

    def open_slots(self, doctor_id: UserId) -> list[domain.Slot]:
        """AVAILABLE slots in (now, now + 14 days) of an active doctor."""
        now = self._clock.now()
        with self._uow.read() as session:
            if doctors_repo.get_active_summary(session, doctor_id, now, now) is None:
                raise NotFoundException()
            return slots_repo.list_open(session, doctor_id, now, now + _OPEN_WINDOW)
