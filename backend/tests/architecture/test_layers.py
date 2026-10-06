"""E6-S2 AC3: import-linter passes on the repo and fails when Repository imports Service."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
RUNNER = "import sys; from importlinter.cli import lint_imports_command as m; sys.exit(m())"


def _lint(cwd: Path, pythonpath: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(pythonpath)}
    return subprocess.run(
        [sys.executable, "-c", RUNNER],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_repository_imports_pass_on_the_repo() -> None:
    result = _lint(BACKEND, BACKEND / "src")
    assert result.returncode == 0, result.stdout + result.stderr


def test_repository_importing_service_breaks_a_contract(tmp_path: Path) -> None:
    shutil.copytree(
        BACKEND / "src", tmp_path / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy(BACKEND / "pyproject.toml", tmp_path / "pyproject.toml")
    offender = tmp_path / "src" / "telemed" / "repository" / "users_repo.py"
    offender.write_text(
        offender.read_text(encoding="utf-8") + "\nimport telemed.service.security  # noqa\n",
        encoding="utf-8",
    )
    result = _lint(tmp_path, tmp_path / "src")
    assert result.returncode != 0
    assert "Repository must not import Service" in result.stdout + result.stderr
