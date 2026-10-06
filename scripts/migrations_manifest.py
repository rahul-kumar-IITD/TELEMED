"""Regenerate or validate backend/alembic/versions.lock.json (sha256 per committed revision).

Usage: python scripts/migrations_manifest.py [--write | --check]
"""
import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
VERSIONS = BACKEND / "alembic" / "versions"
LOCK = BACKEND / "alembic" / "versions.lock.json"


def compute() -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(VERSIONS.glob("*.py"))
        if path.name != "__init__.py"
    }


def load_lock() -> dict[str, str]:
    data: dict[str, str] = json.loads(LOCK.read_text(encoding="utf-8"))
    return data


def violations() -> list[str]:
    """Locked revisions that were modified or deleted."""
    current = compute()
    problems: list[str] = []
    for name, digest in load_lock().items():
        if name not in current:
            problems.append(f"deleted: {name}")
        elif current[name] != digest:
            problems.append(f"modified: {name}")
    return problems


def main(argv: list[str]) -> int:
    if "--write" in argv:
        LOCK.write_text(json.dumps(compute(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    problems = violations()
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
