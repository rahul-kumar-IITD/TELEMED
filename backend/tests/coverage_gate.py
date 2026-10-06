"""Second coverage threshold: the domain layer (telemed.types) must stay at or above 95%."""
import io
import tomllib
from pathlib import Path
from typing import Any

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def load_domain_gate() -> tuple[float, list[str]]:
    """Read the threshold and include globs from [tool.telemed.coverage]."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    cfg = data["tool"]["telemed"]["coverage"]
    return float(cfg["domain_fail_under"]), list(cfg["domain_include"])


def domain_failure(percent: float, minimum: float) -> str | None:
    """Return an error message when domain coverage is below the minimum."""
    if percent < minimum:
        return f"Domain coverage failure: {percent:.2f}% is less than fail-under={minimum:.0f}%"
    return None


def enforce(session: pytest.Session) -> None:
    """Called from pytest_sessionfinish; fails the run when domain coverage is too low."""
    plugin: Any = session.config.pluginmanager.get_plugin("_cov")
    controller = getattr(plugin, "cov_controller", None)
    if plugin is None or controller is None or getattr(plugin, "_disabled", False):
        return
    if session.config.option.collectonly or getattr(controller, "cov", None) is None:
        return
    minimum, include = load_domain_gate()
    percent = float(controller.cov.report(include=include, file=io.StringIO(), skip_empty=True))
    message = domain_failure(percent, minimum)
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if message is not None:
        if reporter is not None:
            reporter.write(f"\nERROR: {message}\n", red=True, bold=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    elif reporter is not None:
        reporter.write(f"\nDomain coverage {percent:.2f}% (required {minimum:.0f}%)\n", green=True)
