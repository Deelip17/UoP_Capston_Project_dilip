"""``aitaf run`` end to end on the sample shop in Chromium (FR-34, NFR-05, NFR-08).

Needs Chromium; excluded from the default run (marker ``integration``). The mock provider
is used, so nothing leaves the machine and nothing is spent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aitaf.cli import main
from aitaf.core.storage import SqliteRepository

pytestmark = [pytest.mark.integration, pytest.mark.blackbox]
ROOT = Path(__file__).resolve().parents[2]


def test_the_whole_pipeline_runs_on_the_demo_shop_and_a_repair_can_be_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    db, out = tmp_path / "p.db", tmp_path / "out"
    code = main(
        [
            "run",
            "--input",
            str(ROOT / "data" / "requirements" / "shop_requirements.md"),
            "--db",
            str(db),
            "--out-dir",
            str(out),
            "--demo-shop",
            "--approve-all",
            "--heal",
            "--mutation",
            "M-login_submit-id",
            "--no-dashboard",
        ]
    )
    assert code == 0
    repo = SqliteRepository(db)
    run_id = repo.latest_run_with_results()
    assert run_id is not None
    results = repo.list_results(run_id)
    assert len(results) >= 40 and any(r.status == "passed" for r in results)
    assert repo.list_failure_analyses(run_id)
    events = [e for e in repo.list_healing_events(run_id) if e.outcome == "proposed"]
    repo.close()
    assert (out / "runs" / run_id / "report.html").exists()
    capsys.readouterr()

    assert main(["dashboard", "--db", str(db), "--out", str(out / "dash")]) == 0
    assert (out / "dash" / "dashboard.html").exists()

    if events:
        event = events[0]
        argv = ["approve-heal", "--db", str(db), "--event", event.event_id]
        assert main([*argv, "--scripts", str(out / "scripts")]) == 0
        repo = SqliteRepository(db)
        stored = {
            loc.loc_id: loc for loc in repo.list_locators(repo.latest_run_with_requirements() or "")
        }
        repo.close()
        assert stored[event.loc_id].version == 2
