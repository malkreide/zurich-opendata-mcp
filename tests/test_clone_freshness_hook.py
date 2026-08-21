"""Zusicherungen für den SessionStart-Hook `.claude/hooks/check-clone-freshness.sh`.

Der Hook ist kein Python, gehört aber zum Repo-Verhalten: Er darf die Session
nie blockieren und darf nur reden, wenn wirklich Commits fehlen. Beides wird
hier gegen echte Git-Repos in `tmp_path` geprüft — ohne Netz.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-clone-freshness.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="Hook-Tests brauchen git und bash",
)


def _git(cwd: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_GLOBAL": str(cwd / ".gitconfig-absent"),
            "GIT_CONFIG_SYSTEM": str(cwd / ".gitconfig-absent"),
        }
    )
    out = subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True
    )
    return out.stdout


def _commit(repo: Path, message: str) -> None:
    (repo / "file.txt").write_text(f"{message}\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", message)


def _make_upstream(tmp_path: Path, branch: str = "master", commits: int = 1) -> Path:
    """Ein Upstream-Repo, dessen Default-Branch frei wählbar ist."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", f"--initial-branch={branch}")
    for index in range(commits):
        _commit(upstream, f"upstream {index}")
    # Aus einem Nicht-Bare-Repo lässt sich klonen, aber nicht in den
    # ausgecheckten Branch pushen — für diese Tests wird nur geklont.
    return upstream


def _clone(tmp_path: Path, upstream: Path) -> Path:
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(upstream), str(clone))
    return clone


def _run_hook(
    project_dir: Path,
    *,
    stdin: str = "",
    timeout_seconds: str = "5",
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["CLAUDE_FRESHNESS_TIMEOUT"] = timeout_seconds
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        cwd=str(project_dir.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_meldet_fehlende_commits_mit_anzahl(tmp_path: Path) -> None:
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    for index in range(3):
        _commit(upstream, f"nach dem Klon {index}")

    result = _run_hook(clone)

    assert result.returncode == 0
    assert "3 Commit(s) hinter origin/master" in result.stdout


def test_ermittelt_default_branch_statt_main_anzunehmen(tmp_path: Path) -> None:
    """`master` als Default-Branch muss erkannt werden, auch ohne origin/HEAD.

    Ohne den lokalen Cache bleibt nur `git ls-remote --symref` — genau der
    Zweig, der bei einem fest verdrahteten `main` an «couldn't find remote ref»
    scheitern würde.
    """
    upstream = _make_upstream(tmp_path, branch="master")
    clone = _clone(tmp_path, upstream)
    _git(clone, "remote", "set-head", "origin", "--delete")
    _commit(upstream, "nach dem Klon")

    result = _run_hook(clone)

    assert result.returncode == 0
    assert "origin/master" in result.stdout
    assert "origin/main" not in result.stdout


def test_schweigt_wenn_der_stand_aktuell_ist(tmp_path: Path) -> None:
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)

    result = _run_hook(clone)

    assert result.returncode == 0
    assert result.stdout == ""


def test_schweigt_bei_eigenen_commits_vor_dem_upstream(tmp_path: Path) -> None:
    """Voraus ist nicht zurück: `HEAD..FETCH_HEAD` zählt nur fehlende Commits."""
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    _commit(clone, "eigene Arbeit")

    result = _run_hook(clone)

    assert result.returncode == 0
    assert result.stdout == ""


def test_zaehlt_auch_bei_detached_head(tmp_path: Path) -> None:
    upstream = _make_upstream(tmp_path, commits=2)
    clone = _clone(tmp_path, upstream)
    _git(clone, "checkout", "--detach", "HEAD~1")
    _commit(upstream, "nach dem Klon")

    result = _run_hook(clone)

    assert result.returncode == 0
    assert "hinter origin/master" in result.stdout


def test_unerreichbares_remote_geht_still_durch(tmp_path: Path) -> None:
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "weg-damit"))
    shutil.rmtree(upstream)

    result = _run_hook(clone)

    assert result.returncode == 0
    assert result.stdout == ""


def _hanging_git_shim(tmp_path: Path, *, with_timeout_cmd: bool) -> tuple[Path, str]:
    """Ein `git`-Shim, das nur bei `fetch` haengt -- Netzausfall ohne Netz.

    `ext::`-Remotes sind in manchen Umgebungen per `GIT_ALLOW_PROTOCOL`
    gesperrt und scheitern dann sofort; der Shim haengt ueberall.
    """
    real_git = shutil.which("git")
    assert real_git is not None
    shim_dir = tmp_path / ("bin-mit-timeout" if with_timeout_cmd else "bin-ohne-timeout")
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text(
        "#!/bin/sh\n"
        'for arg in "$@"; do\n'
        '  [ "$arg" = "fetch" ] && exec sleep 120\n'
        "done\n"
        f'exec {real_git} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)

    if with_timeout_cmd:
        return shim_dir, f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    # PATH ohne `timeout`, damit der Fallback in `run_limited` wirklich laeuft.
    for tool in ("bash", "sh", "sed", "head", "cat", "sleep"):
        found = shutil.which(tool)
        if found is None:  # pragma: no cover - Standardwerkzeug fehlt
            pytest.skip(f"{tool} nicht gefunden")
        (shim_dir / tool).symlink_to(found)
    if shutil.which("timeout", path=str(shim_dir)) is not None:  # pragma: no cover
        pytest.skip("timeout laesst sich hier nicht ausblenden")
    return shim_dir, str(shim_dir)


@pytest.mark.parametrize("with_timeout_cmd", [True, False], ids=["timeout", "fallback"])
def test_haengendes_remote_wird_nach_timeout_abgebrochen(
    tmp_path: Path, with_timeout_cmd: bool
) -> None:
    """Ein Fetch, der nicht antwortet, darf den Sessionstart nicht anhalten.

    Geprueft werden beide Wege in `run_limited`: das `timeout`-Kommando und der
    Fallback fuer Systeme ohne. Ohne die Begrenzung liefe der Fetch 120 Sekunden
    und dieser Test fiele an seinem eigenen Limit. Die untere Schranke stellt
    sicher, dass der Shim wirklich gehangen hat -- ein sofort scheiterndes
    Kommando wuerde den Test sonst aus dem falschen Grund bestehen.
    """
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    _, path_value = _hanging_git_shim(tmp_path, with_timeout_cmd=with_timeout_cmd)

    env = dict(os.environ)
    env["PATH"] = path_value
    env["CLAUDE_PROJECT_DIR"] = str(clone)
    env["CLAUDE_FRESHNESS_TIMEOUT"] = "2"

    started = time.monotonic()
    result = subprocess.run(
        ["bash", str(HOOK)],
        input="",
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    elapsed = time.monotonic() - started

    assert result.returncode == 0
    assert result.stdout == ""
    assert 1.0 < elapsed < 30.0


def test_repo_ohne_remote_geht_still_durch(tmp_path: Path) -> None:
    repo = tmp_path / "solo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _commit(repo, "allein")

    result = _run_hook(repo)

    assert result.returncode == 0
    assert result.stdout == ""


def test_leeres_repo_ohne_head_geht_still_durch(tmp_path: Path) -> None:
    repo = tmp_path / "leer"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")

    result = _run_hook(repo)

    assert result.returncode == 0
    assert result.stdout == ""


def test_ausserhalb_eines_repos_geht_still_durch(tmp_path: Path) -> None:
    plain = tmp_path / "kein-repo"
    plain.mkdir()

    result = _run_hook(plain)

    assert result.returncode == 0
    assert result.stdout == ""


def test_fehlendes_projektverzeichnis_geht_still_durch(tmp_path: Path) -> None:
    ghost = tmp_path / "nie-angelegt"

    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(ghost)
    result = subprocess.run(
        ["bash", str(HOOK)],
        input="",
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("source", ["clear", "compact"])
def test_schweigt_bei_clear_und_compact(tmp_path: Path, source: str) -> None:
    """Zwischen Sessionstart und `compact` ändert sich der Klon nicht."""
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    _commit(upstream, "nach dem Klon")

    result = _run_hook(clone, stdin=f'{{"hook_event_name":"SessionStart","source":"{source}"}}')

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("source", ["startup", "resume"])
def test_meldet_bei_startup_und_resume(tmp_path: Path, source: str) -> None:
    upstream = _make_upstream(tmp_path)
    clone = _clone(tmp_path, upstream)
    _commit(upstream, "nach dem Klon")

    result = _run_hook(clone, stdin=f'{{"hook_event_name":"SessionStart","source":"{source}"}}')

    assert result.returncode == 0
    assert "1 Commit(s) hinter origin/master" in result.stdout


def test_settings_json_registriert_den_hook() -> None:
    """Ein Hook, der nicht registriert ist, schützt nichts."""
    import json

    settings_path = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    commands = [
        hook["command"]
        for matcher in settings["hooks"]["SessionStart"]
        for hook in matcher["hooks"]
    ]

    assert any(HOOK.name in command for command in commands)
    assert HOOK.is_file()
    assert os.access(HOOK, os.X_OK)
