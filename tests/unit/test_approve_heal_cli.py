"""``aitaf approve-heal``: the approval gap between runs is closed (FR-25, NFR-31).

A repair proposed while executing (execution run) is approved by a person; the stored
locator of the run that generated the scripts moves to a new version and, if a scripts
folder is given, the generated locator file is updated too.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.cli import main
from aitaf.core.models import HealingEvent, Locator, LocatorStrategy, Run, RunStatus
from aitaf.core.storage import SqliteRepository
from aitaf.execution import apply_strategy
from aitaf.execution.runner import read_locator_module

NOW = datetime(2026, 11, 16, tzinfo=UTC)
OLD = LocatorStrategy(kind="id", value="old-id")
NEW = LocatorStrategy(kind="id", value="new-id")


def make_db(tmp_path: Path) -> Path:
    db = tmp_path / "a.db"
    repo = SqliteRepository(db)
    for run_id in ("run-src", "run-exec"):
        repo.create_run(
            Run(
                run_id=run_id,
                started_at=NOW,
                status=RunStatus.COMPLETED,
                provider="mock",
                environment="t",
            )
        )
    repo.add_locator(
        "run-src",
        Locator(
            loc_id="shop.add_cart",
            page="shop",
            name="add_cart",
            primary=OLD,
            fallbacks=[],
            model="mock-1",
            prompt_version="sg-v2",
        ),
    )
    repo.add_healing_event(
        "run-exec",
        HealingEvent(
            event_id="ev1",
            run_id="run-exec",
            step_ref="t.py::t#shop.add_cart",
            loc_id="shop.add_cart",
            old_strategy=OLD,
            new_strategy=NEW,
            strategy_used="similarity",
            confidence=0.9,
            validated=True,
            outcome="proposed",
            duration_ms=1,
            created_at=NOW,
        ),
    )
    repo.close()
    return db


def make_scripts(tmp_path: Path) -> Path:
    folder = tmp_path / "scripts" / "locators"
    folder.mkdir(parents=True)
    (folder / "shop_locators.py").write_text(
        'LOCATORS = {"add_cart": {"primary": ("id", "old-id"), "fallbacks": []}}\n',
        encoding="utf-8",
    )
    return folder.parent


@pytest.mark.blackbox
def test_listing_shows_the_repair_as_waiting_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = make_db(tmp_path)
    assert main(["approve-heal", "--db", str(db), "--run", "run-exec"]) == 0
    out = capsys.readouterr().out
    assert "1 proposed locator repair" in out and "ev1" in out and "waiting" in out
    repo = SqliteRepository(db)
    assert repo.list_locators("run-src")[0].version == 1
    repo.close()


@pytest.mark.blackbox
def test_approving_updates_the_stored_locator_and_the_script_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db, scripts = make_db(tmp_path), make_scripts(tmp_path)
    argv = ["approve-heal", "--db", str(db), "--run", "run-exec", "--source-run", "run-src"]
    assert main([*argv, "--event", "ev1", "--scripts", str(scripts)]) == 0
    assert "version 2" in capsys.readouterr().out
    repo = SqliteRepository(db)
    stored = repo.list_locators("run-src")[0]
    assert stored.version == 2 and stored.primary == NEW and stored.fallbacks == [OLD]
    assert repo.list_healing_events("run-exec")[0].approved
    repo.close()
    module = read_locator_module(scripts / "locators" / "shop_locators.py")
    assert module is not None and module["add_cart"]["primary"] == ("id", "new-id")
    assert "approved locator update" in (scripts / "locators" / "shop_locators.py").read_text(
        "utf-8"
    )


@pytest.mark.whitebox
def test_an_unknown_event_is_reported_and_nothing_changes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = make_db(tmp_path)
    assert main(["approve-heal", "--db", str(db), "--run", "run-exec", "--event", "nope"]) == 1
    assert "no proposed healing event" in capsys.readouterr().err
    repo = SqliteRepository(db)
    assert repo.list_locators("run-src")[0].version == 1
    repo.close()


@pytest.mark.whitebox
def test_apply_strategy_keeps_the_old_primary_and_ignores_unknown_names(tmp_path: Path) -> None:
    scripts = make_scripts(tmp_path)
    assert apply_strategy(scripts, "shop", "missing", NEW) is False
    assert apply_strategy(scripts, "nopage", "add_cart", NEW) is False
    assert apply_strategy(scripts, "shop", "add_cart", NEW) is True
    module = read_locator_module(scripts / "locators" / "shop_locators.py")
    assert module is not None
    assert module["add_cart"]["primary"] == ("id", "new-id")
    assert module["add_cart"]["fallbacks"] == [("id", "old-id")]
    assert "one run, needs approval" in (scripts / "locators" / "shop_locators.py").read_text(
        "utf-8"
    )
