"""Fixtures for the acceptance tests of FR-01 to FR-16 (Unit 7, ADR-046, ADR-047).

The author acts as the customer: each test checks one acceptance criterion through the real
command line or the public package API, with the mock provider, no browser and no network.
Tests get the helpers as fixtures (``run_cli``, ``scripted``) instead of importing this file,
because several ``conftest.py`` files with the same name exist in the test tree.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from aitaf.core.models import ReviewStatus
from aitaf.core.storage import SqliteRepository

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "data" / "requirements"
SHOP_PAGES = ROOT / "data" / "dom" / "shop"
_STRIPPED = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "LLM_PRICE_IN_PER_1K", "LLM_PRICE_OUT_PER_1K")

RunCli = Callable[..., "subprocess.CompletedProcess[str]"]


def _environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["LLM_PROVIDER"] = "mock"
    for name in _STRIPPED:
        env.pop(name, None)
    env.update(extra or {})
    return env


def _cli(
    *args: str, extra_env: dict[str, str] | None = None, timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aitaf", *args],
        cwd=ROOT,
        env=_environment(extra_env),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(scope="session")
def run_cli() -> RunCli:
    """Run ``python -m aitaf ...`` the way a person would (mock provider, no key)."""
    return _cli


@dataclass(frozen=True)
class Scripted:
    """One real analyze, generate, approve and script run on the 20 shop requirements."""

    db: Path
    run_id: str
    gen: Path
    export: Path
    analyze_out: str
    generate_out: str
    script_out: str

    def repo(self) -> SqliteRepository:
        return SqliteRepository(self.db)


@pytest.fixture(scope="module")
def scripted(tmp_path_factory: pytest.TempPathFactory) -> Scripted:
    root = tmp_path_factory.mktemp("acceptance")
    db, gen, export = root / "a.db", root / "gen", root / "export"
    analysed = _cli(
        "analyze", "--input", str(REQUIREMENTS / "shop_requirements.md"), "--db", str(db)
    )
    generated = _cli("generate", "--db", str(db), "--export-dir", str(export))
    assert analysed.returncode == 0 and generated.returncode == 0, generated.stderr[-800:]
    repo = SqliteRepository(db)
    try:
        run_id = repo.latest_run_with_requirements()
        assert run_id is not None
        for case in repo.list_test_cases(run_id):
            repo.set_review_status(run_id, case.tc_id, ReviewStatus.APPROVED)
    finally:
        repo.close()
    script = _cli("script", "--db", str(db), "--out-dir", str(gen), "--pages", str(SHOP_PAGES))
    assert script.returncode == 0, script.stderr[-800:]
    return Scripted(
        db=db,
        run_id=run_id,
        gen=gen,
        export=export,
        analyze_out=analysed.stdout,
        generate_out=generated.stdout,
        script_out=script.stdout,
    )
