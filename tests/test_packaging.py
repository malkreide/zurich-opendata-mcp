"""Guards on the declared dependency range.

The defect these tests exist for: `0.5.1` shipped with `mcp[cli]>=1.28.1` and
no upper bound. When `mcp` 2.0.0 removed `mcp.server.fastmcp`, every free
resolve picked it up and the published wheel died at import — while CI, which
resolves from the lockfile, stayed green.

Two independent claims are checked here, because the lockfile can hide either:

  1. the declared range is bounded on both ends, so a resolver cannot walk
     into a major version this code has never been run against;
  2. the range and the source agree on *which* API is in use — a floor of
     `>=2.0.0` means nothing if some module still imports the 1.x path.

`scripts/smoke_installed.py` covers the third claim, that the built artifact
actually starts. That one needs a real install and lives in CI.
"""

from __future__ import annotations

import re
import tomllib
from importlib.metadata import version as distribution_version
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _dependencies() -> list[Requirement]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return [Requirement(dep) for dep in pyproject["project"]["dependencies"]]


def _mcp_requirement() -> Requirement:
    for req in _dependencies():
        if req.name == "mcp":
            return req
    raise AssertionError("pyproject.toml declares no `mcp` dependency")


def test_every_runtime_dependency_has_a_lower_bound():
    """An unpinned floor lets a resolver pick a version predating a needed API."""
    for req in _dependencies():
        operators = {spec.operator for spec in req.specifier}
        assert operators & {">=", "==", "~="}, (
            f"{req.name} declares no lower bound ({str(req.specifier)!r}); "
            "a resolver may pick an arbitrarily old version"
        )


def test_mcp_requirement_is_capped():
    """The regression guard for the 0.5.1 defect.

    `mcp` is the one dependency whose server API this package imports directly,
    and 2.0.0 removed that module outright. An uncapped range hands the choice
    of major version to whoever installs the package next.
    """
    req = _mcp_requirement()
    operators = {spec.operator for spec in req.specifier}
    assert operators & {"<", "<=", "==", "~="}, (
        f"mcp is declared as {str(req.specifier)!r} with no upper bound — this is "
        "the exact shape that shipped a broken 0.5.1: `mcp` 2.0.0 removed "
        "`mcp.server.fastmcp` and every fresh resolve took it."
    )


def test_installed_mcp_satisfies_the_declared_range():
    """Catches the lockfile drifting outside what pyproject.toml promises.

    The test suite runs against the locked resolve. If the lock and the
    declared range disagree, a green suite says nothing about what a user gets.
    """
    req = _mcp_requirement()
    installed = distribution_version("mcp")
    assert req.specifier.contains(Version(installed), prereleases=True), (
        f"installed mcp {installed} is outside the declared range "
        f"{str(req.specifier)!r} — the tests are measuring a resolve that no "
        "user can reproduce"
    )


def test_source_imports_the_api_the_floor_promises():
    """`>=2.0.0` and `mcp.server.fastmcp` cannot both be true."""
    offenders = [
        str(path.relative_to(ROOT))
        for path in sorted(SRC.rglob("*.py"))
        if re.search(r"\bmcp\.server\.fastmcp\b", path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        f"{offenders} import `mcp.server.fastmcp`, removed in mcp 2.0.0, while "
        f"pyproject.toml declares mcp{_mcp_requirement().specifier}"
    )

    used = [
        path
        for path in sorted(SRC.rglob("*.py"))
        if re.search(r"\bmcp\.server\.mcpserver\b", path.read_text(encoding="utf-8"))
    ]
    assert used, "no module imports `mcp.server.mcpserver` — is the 2.x floor still right?"
