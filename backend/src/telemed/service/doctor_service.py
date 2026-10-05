"""Admin onboarding of doctors: validate, then create everything in one transaction."""
import logging
from decimal import Decimal

from telemed.config.clock import Clock
from telemed.repository import doctors_repo, users_repo
from telemed.service import security
from telemed.service.slot_generator import SlotGenerator
from telemed.service.unit_of_work import UnitOfWork
from telemed.types.domain import DoctorOnboarding, OnboardedDoctor, StoredTemplate, TemplateSpec
from telemed.types.enums import Role
from telemed.types.errors import FieldError, InputValidationException
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
