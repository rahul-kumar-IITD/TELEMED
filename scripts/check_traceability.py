"""Traceability gate: every AC-01..AC-10 and NFR-01..NFR-08 needs at least one tagged test.

Python tests are tagged with ``@pytest.mark.ac("AC-01")`` / ``@pytest.mark.nfr("NFR-01")``;
vitest and Playwright tests carry the ID in the ``it``/``test``/``describe`` title.
Usage: python scripts/check_traceability.py [repo_root]   (exit 1 when any ID has no test)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED: tuple[str, ...] = (
    *(f"AC-{n:02d}" for n in range(1, 11)),
    *(f"NFR-{n:02d}" for n in range(1, 9)),
)
PY_MARK = re.compile(r"""mark\.(?:ac|nfr)\(\s*["']((?:AC|NFR)-\d{2})["']""")
TS_TITLE = re.compile(r"""\b(?:it|test|describe)(?:\.\w+)?\(\s*(["'`])(.*?)\1""")
ID_IN_TITLE = re.compile(r"\b(?:AC|NFR)-\d{2}\b")
SELF_TESTS = {"test_traceability.py"}
SKIP_DIRS = {"node_modules", "__pycache__", ".venv", ".git"}


def _files(root: Path, base: str, suffixes: tuple[str, ...]) -> list[Path]:
    start = root / base
    if not start.is_dir():
        return []
    return [
        p
        for p in start.rglob("*")
        if p.suffix in suffixes
        and p.name not in SELF_TESTS
        and not SKIP_DIRS.intersection(p.parts)
    ]


def scan(root: Path) -> dict[str, int]:
    """Return the number of tagged tests found for every required ID."""
    counts = dict.fromkeys(REQUIRED, 0)
    for path in _files(root, "backend/tests", (".py",)):
        for tag in PY_MARK.findall(path.read_text(encoding="utf-8")):
            if tag in counts:
                counts[tag] += 1
    for base in ("frontend/tests", "e2e", "tests"):
        for path in _files(root, base, (".ts", ".tsx")):
            for _quote, title in TS_TITLE.findall(path.read_text(encoding="utf-8")):
                for tag in ID_IN_TITLE.findall(title):
                    if tag in counts:
                        counts[tag] += 1
    return counts


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    counts = scan(root)
    for tag, count in counts.items():
        print(f"{tag}: {count} test(s)")
    missing = [tag for tag, count in counts.items() if count == 0]
    if missing:
        print(f"MISSING tagged tests for: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
