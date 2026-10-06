"""Idempotent synthetic demo data: one admin, several doctors and patients, and their slots.

Everything is marked synthetic by the reserved `@example.test` domain. Doctors are created
through DoctorService.onboard, which fills their 14-day window via the slot generator.
"""
from dataclasses import dataclass

from telemed.config.clock import Clock
from telemed.repository import users_repo
from telemed.service import security
from telemed.service.auth_service import AuthService
from telemed.service.doctor_service import DoctorService
from telemed.service.unit_of_work import UnitOfWork
from telemed.types.domain import DoctorOnboarding, ProfileData, TemplateSpec
from telemed.types.enums import Gender, Role

ADMIN_EMAIL = "admin@example.test"
# Synthetic demo credential for local demonstrations only; override with SEED_PASSWORD.
DEFAULT_DEMO_PASSWORD = "Demo-Passw0rd-1"


def _weekdays(start: str, end: str) -> tuple[TemplateSpec, ...]:
    return tuple(TemplateSpec(day, start, end, 30) for day in range(7))


_DOCTORS = (
    ("dr.rao@example.test", "Dr. Asha Rao (demo)", "Cardiology", ("en", "hi"), "500.00"),
    ("dr.iyer@example.test", "Dr. Vikram Iyer (demo)", "Dermatology", ("en", "ta"), "400.00"),
    ("dr.khan@example.test", "Dr. Sara Khan (demo)", "Pediatrics", ("en", "ur"), "350.00"),
)
_PATIENTS = tuple(
    (f"patient{n}@example.test", f"Demo Patient {n}", 25 + n) for n in range(1, 6)
)


@dataclass(frozen=True)
class SeedSummary:
    users_created: int
    slots_created: int


class SeedService:
    def __init__(
        self, uow: UnitOfWork, clock: Clock, auth: AuthService, doctors: DoctorService
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._auth = auth
        self._doctors = doctors

    def _exists(self, email: str) -> bool:
        with self._uow.read() as session:
            return users_repo.find_credentials_by_email(session, email) is not None

    def run(self, password: str) -> SeedSummary:
        """Create whatever is missing (existence checked by email); safe to run repeatedly."""
        users = int(self._seed_admin(password))
        slots = 0
        for email, name, specialty, languages, fee in _DOCTORS:
            if self._exists(email):
                continue
            details = DoctorOnboarding(
                email=email, full_name=name, specialty=specialty, languages=languages,
                fee=fee, templates=_weekdays("09:00", "12:00"),
            )
            slots += self._doctors.onboard(details, password).slots_created
            users += 1
        for email, name, age in _PATIENTS:
            if self._exists(email):
                continue
            profile = ProfileData(name, age, Gender.UNDISCLOSED, "0000000")
            self._auth.register(email, password, profile)
            users += 1
        return SeedSummary(users_created=users, slots_created=slots)

    def _seed_admin(self, password: str) -> bool:
        if self._exists(ADMIN_EMAIL):
            return False
        password_hash = security.hash_password(password)  # before the write lock
        with self._uow.transaction() as session:
            users_repo.insert_user(
                session, ADMIN_EMAIL, password_hash, Role.ADMIN, self._clock.now()
            )
        return True
