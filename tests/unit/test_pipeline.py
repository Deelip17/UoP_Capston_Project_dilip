"""``aitaf run``: stage order, the human-approval gate and the usage errors (FR-34, NFR-05).

A fake stage runner records what the orchestrator would run, so no model, browser or
server is needed; the real end-to-end run is in ``tests/integration/test_pipeline_shop.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from pipeline_records import SOURCE, case, requirement, run

from aitaf.core.errors import ConfigError
from aitaf.core.models import ReviewStatus
from aitaf.core.storage import SqliteRepository
from aitaf.pipeline import add_arguments, run_pipeline


def parse(tmp_path: Path, *extra: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return parser.parse_args(
        [
            "--input",
            "req.md",
            "--db",
            str(tmp_path / "sub" / "p.db"),
            "--out-dir",
            str(tmp_path / "o"),
            *extra,
        ]
    )


class FakeStages:
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[list[str]] = []
        self.fail_on = fail_on

    def __call__(self, argv: list[str]) -> int:
        self.calls.append(argv)
        return 5 if argv[0] == self.fail_on else 0

    @property
    def names(self) -> list[str]:
        return [call[0] for call in self.calls]


def seed(db: str) -> None:
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    repo = SqliteRepository(db)
    repo.create_run(run(SOURCE))
    repo.add_requirement(SOURCE, requirement("R1"))
    repo.add_test_case(SOURCE, case("TC-1", "R1", ReviewStatus.PENDING))
    repo.close()


@pytest.mark.blackbox
def test_without_approval_the_run_stops_at_the_human_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stages = FakeStages()
    assert run_pipeline(parse(tmp_path, "--demo-shop"), stages) == 0
    assert stages.names == ["analyze", "generate"]
    assert "human gate" in capsys.readouterr().out


@pytest.mark.blackbox
def test_with_approve_all_every_stage_runs_in_order(tmp_path: Path) -> None:
    args = parse(tmp_path, "--demo-shop", "--approve-all")
    seed(args.db)
    stages = FakeStages()
    assert run_pipeline(args, stages) == 0
    assert stages.names == [
        "analyze",
        "generate",
        "script",
        "execute",
        "diagnose",
        "report",
        "dashboard",
    ]
    repo = SqliteRepository(args.db)
    assert {c.review_status for c in repo.list_test_cases(SOURCE)} == {ReviewStatus.APPROVED}
    repo.close()


@pytest.mark.whitebox
def test_the_demo_shop_url_reaches_script_and_execute_with_heal_and_pages(tmp_path: Path) -> None:
    args = parse(tmp_path, "--demo-shop", "--approve-all", "--heal", "--no-dashboard")
    stages = FakeStages()
    run_pipeline(args, stages)
    script, execute = stages.calls[2], stages.calls[3]
    url = script[script.index("--base-url") + 1]
    assert url.startswith("http://127.0.0.1:") and execute[execute.index("--base-url") + 1] == url
    assert "--pages" in script and "--heal" in execute and "--baseline" in execute
    assert "dashboard" not in stages.names


@pytest.mark.whitebox
def test_a_failing_stage_stops_the_pipeline_with_its_exit_code(tmp_path: Path) -> None:
    stages = FakeStages(fail_on="generate")
    assert run_pipeline(parse(tmp_path, "--demo-shop", "--approve-all"), stages) == 5
    assert stages.names == ["analyze", "generate"]


@pytest.mark.whitebox
def test_failing_tests_do_not_stop_the_pipeline(tmp_path: Path) -> None:
    class ExitOneOnExecute(FakeStages):
        def __call__(self, argv: list[str]) -> int:
            super().__call__(argv)
            return 1 if argv[0] == "execute" else 0

    stages = ExitOneOnExecute()
    assert run_pipeline(parse(tmp_path, "--demo-shop", "--approve-all"), stages) == 0
    assert stages.names[-3:] == ["diagnose", "report", "dashboard"]


@pytest.mark.whitebox
def test_a_system_under_test_is_required_and_a_mutation_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="--demo-shop or --base-url"):
        run_pipeline(parse(tmp_path), FakeStages())
    bad = parse(tmp_path, "--demo-shop", "--approve-all", "--mutation", "M-nothing")
    with pytest.raises(ConfigError, match="unknown mutation"):
        run_pipeline(bad, FakeStages())


@pytest.mark.whitebox
def test_a_given_base_url_is_used_as_it_is(tmp_path: Path) -> None:
    args = parse(tmp_path, "--base-url", "http://shop.test", "--allow-host", "shop.test")
    args.approve_all = True
    stages = FakeStages()
    run_pipeline(args, stages)
    execute = stages.calls[3]
    assert execute[execute.index("--base-url") + 1] == "http://shop.test"
    assert "--allow-host" in execute and "--pages" not in stages.calls[2]
