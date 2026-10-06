"""Create synthetic demo data (idempotent). Usage: uv run python scripts/seed.py"""
import os
import sys

from telemed.service import bootstrap
from telemed.service.container import build_container
from telemed.service.seed_service import DEFAULT_DEMO_PASSWORD, SeedService


def main() -> int:
    container = build_container(bootstrap.bootstrap())
    try:
        service = SeedService(
            container.uow, container.clock, container.auth, container.doctors
        )
        summary = service.run(os.environ.get("SEED_PASSWORD", DEFAULT_DEMO_PASSWORD))
    finally:
        container.uow.dispose()
    print(f"seed complete: {summary.users_created} users, {summary.slots_created} slots created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
