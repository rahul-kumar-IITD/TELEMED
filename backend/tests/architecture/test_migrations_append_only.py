"""E1-S1 AC6: migrations are append-only (NFR-05)."""
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

from telemed.repository.triggers import APPEND_ONLY_TABLES

ROOT = Path(__file__).resolve().parents[3]
VERSIONS = ROOT / "backend" / "alembic" / "versions"
_TABLES = "|".join(APPEND_ONLY_TABLES)
FORBIDDEN = re.compile(
    rf"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?({_TABLES})\b"
    rf"|DELETE\s+FROM\s+({_TABLES})\b"
    rf"|UPDATE\s+({_TABLES})\s+SET\b"
    rf"|ALTER\s+TABLE\s+({_TABLES})\b"
    r"|DROP\s+TRIGGER\b"
    rf"|drop_table\(\s*['\"]({_TABLES})['\"]"
    rf"|batch_alter_table\(\s*['\"]({_TABLES})['\"]",
    re.IGNORECASE,
)


def _manifest() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "migrations_manifest", ROOT / "scripts" / "migrations_manifest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.ac("AC-E1-S1-6")
def test_committed_revisions_unmodified_and_present() -> None:
    assert _manifest().violations() == []


@pytest.mark.ac("AC-E1-S1-6")
def test_lock_covers_every_revision() -> None:
    lock = json.loads((VERSIONS.parent / "versions.lock.json").read_text(encoding="utf-8"))
    names = {p.name for p in VERSIONS.glob("*.py") if p.name != "__init__.py"}
    assert names == set(lock)
    assert "0001_initial_schema.py" in lock


@pytest.mark.ac("AC-E1-S1-6")
def test_manifest_detects_modification_and_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _manifest()
    fake_versions = tmp_path / "versions"
    fake_versions.mkdir()
    (fake_versions / "0001_a.py").write_text("x = 1\n", encoding="utf-8")
    (fake_versions / "0002_b.py").write_text("y = 1\n", encoding="utf-8")
    monkeypatch.setattr(module, "VERSIONS", fake_versions)
    monkeypatch.setattr(module, "LOCK", tmp_path / "lock.json")
    assert module.main(["--write"]) == 0
    assert module.main([]) == 0
    (fake_versions / "0001_a.py").write_text("x = 2\n", encoding="utf-8")
    (fake_versions / "0002_b.py").unlink()
    assert sorted(module.violations()) == ["deleted: 0002_b.py", "modified: 0001_a.py"]
    assert module.main([]) == 1


@pytest.mark.ac("AC-E1-S1-6")
def test_no_migration_drops_or_rewrites_append_only_tables() -> None:
    for path in VERSIONS.glob("*.py"):
        assert FORBIDDEN.search(path.read_text(encoding="utf-8")) is None, path.name


@pytest.mark.parametrize(
    "bad",
    [
        "DROP TABLE appointment_events",
        "DELETE FROM consultation_notes",
        "UPDATE patient_profile_versions SET age = 1",
        "ALTER TABLE consultation_notes ADD COLUMN x TEXT",
        "DROP TRIGGER trg_ae_no_update",
        "op.drop_table('appointment_events')",
    ],
)
def test_forbidden_pattern_flags_bad_migrations(bad: str) -> None:
    assert FORBIDDEN.search(bad) is not None
