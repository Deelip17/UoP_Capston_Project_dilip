"""Run the real command line and the whole pipeline in a subprocess (system and acceptance tests).

Every scenario drives ``python -m aitaf`` the way a person would, against the local demo shop
with the mock provider, so nothing leaves the machine and nothing costs money.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from aitaf.core.storage import SqliteRepository

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "data" / "requirements" / "shop_requirements.md"
SAMPLE_PLAIN = ROOT / "data" / "requirements" / "sample_plain.txt"
# Every strategy of the password locator (id, class, test hook) is broken, so the generated
# fallbacks cannot save the step and the Self-Healing Engine is really needed.
BREAK_PASSWORD = ("M-password-id", "M-password-class", "M-password-xpath")
_STRIPPED = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "LLM_PRICE_IN_PER_1K", "LLM_PRICE_OUT_PER_1K")


def environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["LLM_PROVIDER"] = "mock"
    for name in _STRIPPED:
        env.pop(name, None)
    env.update(extra or {})
    return env


def cli(
    *args: str, extra_env: dict[str, str] | None = None, timeout: int = 900
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aitaf", *args],
        cwd=ROOT,
        env=environment(extra_env),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def kill_tree(process: subprocess.Popen[str]) -> None:
    """Stop a command and everything it started (the engine starts PyTest and a browser)."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=30)


@dataclass(frozen=True)
class Pipeline:
    """One finished ``aitaf run`` with everything a scenario may inspect."""

    process: subprocess.CompletedProcess[str]
    out: Path
    db: Path

    def repo(self) -> SqliteRepository:
        return SqliteRepository(self.db)

    @property
    def exec_run(self) -> str:
        repo = self.repo()
        try:
            run_id = repo.latest_run_with_results()
        finally:
            repo.close()
        assert run_id is not None, self.process.stdout[-800:]
        return run_id


def run_pipeline(root: Path, name: str) -> Pipeline:
    out, db = root / name, root / f"{name}.db"
    process = cli(
        "run",
        "--input",
        str(REQUIREMENTS),
        "--db",
        str(db),
        "--out-dir",
        str(out),
        "--demo-shop",
        "--approve-all",
        "--heal",
        *[arg for mutation in BREAK_PASSWORD for arg in ("--mutation", mutation)],
    )
    return Pipeline(process=process, out=out, db=db)


def copy_pipeline(source: Pipeline, target: Path) -> Pipeline:
    """A private copy for a scenario that changes files (the approval scenario)."""
    shutil.copytree(source.out, target / "out")
    shutil.copy(source.db, target / "p.db")
    return Pipeline(process=source.process, out=target / "out", db=target / "p.db")
