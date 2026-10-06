"""E6-S2 AC2/AC5: the traceability script passes on the repo and fails when a tag is missing."""
import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "check_traceability.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_traceability", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scratch(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


def _all_python_tags() -> str:
    marks = [f'@pytest.mark.ac("AC-{n:02d}")' for n in range(1, 11)]
    marks += [f'@pytest.mark.nfr("NFR-{n:02d}")' for n in range(1, 9)]
    return "\n".join(marks)


def test_repo_has_every_tag() -> None:
    module = _load()
    counts = module.scan(REPO)
    assert sorted(counts) == sorted(module.REQUIRED)
    assert all(count >= 1 for count in counts.values()), counts
    assert module.main(["check_traceability.py", str(REPO)]) == 0


def test_missing_ac_tag_exits_non_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _all_python_tags().replace('@pytest.mark.ac("AC-05")', "")
    root = _scratch(tmp_path, {"backend/tests/test_x.py": text})
    assert _load().main(["x", str(root)]) == 1
    assert "AC-05" in capsys.readouterr().err


def test_missing_nfr_tag_exits_non_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = _all_python_tags().replace('@pytest.mark.nfr("NFR-03")', "")
    root = _scratch(tmp_path, {"backend/tests/test_x.py": text})
    assert _load().main(["x", str(root)]) == 1
    assert "NFR-03" in capsys.readouterr().err


def test_frontend_titles_count_as_tags(tmp_path: Path) -> None:
    text = _all_python_tags().replace('@pytest.mark.ac("AC-02")', "")
    root = _scratch(
        tmp_path,
        {
            "backend/tests/test_x.py": text,
            "frontend/tests/unit/a.test.tsx": 'it("AC-02 lists doctors", () => {});',
        },
    )
    assert _load().scan(root)["AC-02"] == 1
    assert _load().main(["x", str(root)]) == 0
    shutil.rmtree(root / "frontend")
    assert _load().main(["x", str(root)]) == 1
