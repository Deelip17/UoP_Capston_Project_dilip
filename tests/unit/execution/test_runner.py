"""Execution Engine tests with a fake browser fixture (FR-17 to FR-21, NFR-11, NFR-23).

The engine runs a generated-style project with real PyTest in a subprocess. A fake
``page`` fixture replaces the browser so the tests need no browser and finish in
seconds; the real-browser run is in ``tests/integration``.
"""

from __future__ import annotations

import json
import os
import textwrap
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.errors import ExecutionError, PolicyError
from aitaf.core.logging import set_run_id
from aitaf.core.metrics import Metrics
from aitaf.core.models import Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.execution import ExecutionEngine, RunConfig

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)

CONFTEST = """
import pytest


def pytest_addoption(parser):
    parser.addoption("--base-url", default="http://127.0.0.1:1")


class FakePage:
    def screenshot(self, path):
        with open(path, "wb") as handle:
            handle.write(b"\\x89PNG fake")

    def content(self):
        return "<html>fake</html>"


@pytest.fixture
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture
def page():
    yield FakePage()
"""


def project(tmp_path: Path, tests: dict[str, str], manifest: bool = True) -> Path:
    root = tmp_path / "scripts"
    (root / "tests").mkdir(parents=True)
    (root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    entries = []
    for name, source in tests.items():
        (root / "tests" / f"{name}.py").write_text(textwrap.dedent(source), encoding="utf-8")
        entries.append(
            {
                "script_id": f"SCR-{name}",
                "tc_id": name.upper().replace("_", "-"),
                "path": f"tests/{name}.py",
            }
        )
    if manifest:
        (root / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")
    return root


def config(root: Path, tmp_path: Path, **extra: object) -> RunConfig:
    base: dict[str, object] = {
        "scripts_dir": root,
        "base_url": "http://127.0.0.1:8765",
        "allowed_hosts": ["127.0.0.1"],
        "evidence_dir": tmp_path / "evidence",
        "run_timeout_s": 120,
    }
    return RunConfig(**{**base, **extra})  # type: ignore[arg-type]


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=NOW,
            status=RunStatus.RUNNING,
            provider="mock",
            environment="test",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


MIXED = {
    "test_pass": "def test_pass(page):\n    assert True\n",
    "test_fail": "def test_fail(page):\n    assert 'a' == 'b', 'labels differ'\n",
    "test_skip": (
        "import pytest\n\n@pytest.mark.skip(reason='later')\ndef test_skip(page):\n    pass\n"
    ),
    "test_error": (
        "import pytest\n\n@pytest.fixture\ndef broken():\n    raise RuntimeError('no data')\n\n"
        "def test_error(page, broken):\n    pass\n"
    ),
}


@pytest.mark.blackbox
def test_results_of_every_kind_are_stored_and_queryable_after_the_run(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, MIXED)
    summary = ExecutionEngine(repo).execute(config(root, tmp_path))
    stored = {r.tc_id: r for r in repo.list_results("run-1")}
    assert {tc: r.status for tc, r in stored.items()} == {
        "TEST-PASS": "passed",
        "TEST-FAIL": "failed",
        "TEST-SKIP": "skipped",
        "TEST-ERROR": "error",
    }
    assert (summary.passed, summary.failed, summary.errors, summary.skipped) == (1, 1, 1, 1)
    assert all(r.duration_ms >= 0 and r.attempts == 1 for r in stored.values())
    assert "labels differ" in stored["TEST-FAIL"].log


@pytest.mark.blackbox
def test_a_failing_test_has_a_linked_screenshot_and_dom_snapshot(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, MIXED)
    ExecutionEngine(repo).execute(config(root, tmp_path))
    failed = next(r for r in repo.list_results("run-1") if r.tc_id == "TEST-FAIL")
    assert (tmp_path / "evidence" / failed.screenshot).read_bytes().startswith(b"\x89PNG")
    assert "fake" in (tmp_path / "evidence" / failed.dom_snapshot).read_text(encoding="utf-8")
    passed = next(r for r in repo.list_results("run-1") if r.tc_id == "TEST-PASS")
    assert passed.screenshot == ""


@pytest.mark.blackbox
def test_a_junit_report_is_written_for_the_run(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, MIXED)
    summary = ExecutionEngine(repo).execute(config(root, tmp_path))
    assert summary.junit_path.read_text(encoding="utf-8").startswith("<?xml")


@pytest.mark.blackbox
def test_a_non_listed_url_aborts_before_anything_runs(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """FR-21: the run is refused before PyTest or any browser starts."""
    root = project(tmp_path, MIXED)
    engine = ExecutionEngine(repo, python="this-interpreter-does-not-exist")
    with pytest.raises(PolicyError, match="allow-list"):
        engine.execute(config(root, tmp_path, base_url="http://www.example.org"))
    assert repo.list_results("run-1") == []
    assert not (tmp_path / "evidence").exists()


@pytest.mark.blackbox
def test_a_flaky_test_is_retried_and_the_attempts_are_recorded(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    marker = tmp_path / "seen-once"
    flaky = (
        "import os\n\ndef test_flaky(page):\n"
        f"    marker = {str(marker)!r}\n"
        "    if not os.path.exists(marker):\n"
        "        open(marker, 'w').close()\n"
        "        assert False, 'first attempt fails'\n"
    )
    root = project(
        tmp_path, {"test_flaky": flaky, "test_broken": "def test_broken(page):\n    assert False\n"}
    )
    ExecutionEngine(repo).execute(config(root, tmp_path, retries=2))
    stored = {r.tc_id: r for r in repo.list_results("run-1")}
    assert stored["TEST-FLAKY"].status == "passed" and stored["TEST-FLAKY"].attempts == 2
    assert stored["TEST-BROKEN"].status == "failed" and stored["TEST-BROKEN"].attempts == 3


@pytest.mark.blackbox
def test_without_retries_a_failure_is_final(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, {"test_broken": "def test_broken(page):\n    assert False\n"})
    ExecutionEngine(repo).execute(config(root, tmp_path, retries=0))
    (only,) = repo.list_results("run-1")
    assert only.attempts == 1


@pytest.mark.blackbox
def test_parallel_workers_record_every_test_once(repo: InMemoryRepository, tmp_path: Path) -> None:
    tests = {f"test_case_{i}": f"def test_case_{i}(page):\n    assert True\n" for i in range(6)}
    root = project(tmp_path, tests)
    summary = ExecutionEngine(repo).execute(config(root, tmp_path, workers=2))
    assert summary.passed == 6
    assert sorted(r.tc_id for r in repo.list_results("run-1")) == sorted(
        name.upper().replace("_", "-") for name in tests
    )


@pytest.mark.blackbox
def test_secrets_in_the_parent_environment_do_not_reach_the_tests(
    repo: InMemoryRepository, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-11: least privilege; the browser tests never see the API key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-parent-value-1234567890")
    monkeypatch.setenv("MY_SERVICE_TOKEN", "token-value")
    probe = (
        "import os\n\ndef test_probe(page):\n"
        "    assert 'OPENAI_API_KEY' not in os.environ\n"
        "    assert 'MY_SERVICE_TOKEN' not in os.environ\n"
        "    assert 'PATH' in os.environ\n"
    )
    root = project(tmp_path, {"test_probe": probe})
    summary = ExecutionEngine(repo).execute(config(root, tmp_path))
    assert summary.passed == 1, [r.log for r in repo.list_results("run-1")]


@pytest.mark.blackbox
def test_secrets_in_failure_output_are_masked_before_storage(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    leaky = "def test_leak(page):\n    assert False, 'key was sk-live-ABCDEF1234567890ABCDEF12'\n"
    root = project(tmp_path, {"test_leak": leaky})
    ExecutionEngine(repo).execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert "sk-live-ABCDEF1234567890ABCDEF12" not in result.log
    assert result.status == "failed"


@pytest.mark.whitebox
def test_the_tc_id_comes_from_the_manifest_and_falls_back_to_the_file_name(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(
        tmp_path,
        {"test_tc_3f03ebef_01": "def test_tc_3f03ebef_01(page):\n    pass\n"},
        manifest=False,
    )
    ExecutionEngine(repo).execute(config(root, tmp_path))
    (result,) = repo.list_results("run-1")
    assert result.tc_id == "TC-3F03EBEF-01"
    (root / "manifest.json").write_text(
        json.dumps([{"tc_id": "TC-FROM-MANIFEST", "path": "tests/test_tc_3f03ebef_01.py"}]),
        encoding="utf-8",
    )
    ExecutionEngine(repo).execute(config(root, tmp_path))
    assert repo.list_results("run-1")[-1].tc_id == "TC-FROM-MANIFEST"


@pytest.mark.whitebox
def test_run_level_timing_is_recorded_as_a_metric(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = project(tmp_path, {"test_pass": "def test_pass(page):\n    pass\n"})
    ExecutionEngine(repo, metrics=Metrics(repo)).execute(config(root, tmp_path))
    samples = repo.list_metrics("run-1")
    assert [(s.component, s.operation, s.outcome) for s in samples] == [
        ("execution_engine", "run", "ok")
    ]
    assert samples[0].duration_ms > 0


@pytest.mark.whitebox
def test_a_directory_without_tests_is_an_error(repo: InMemoryRepository, tmp_path: Path) -> None:
    root = tmp_path / "empty"
    (root / "tests").mkdir(parents=True)
    (root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    with pytest.raises(ExecutionError, match="no test"):
        ExecutionEngine(repo).execute(config(root, tmp_path))


@pytest.mark.whitebox
def test_a_missing_scripts_directory_is_an_error(repo: InMemoryRepository, tmp_path: Path) -> None:
    with pytest.raises(ExecutionError, match="scripts directory"):
        ExecutionEngine(repo).execute(config(tmp_path / "nowhere", tmp_path))


@pytest.mark.whitebox
def test_a_run_that_exceeds_the_time_limit_is_stopped(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    slow = "import time\n\ndef test_slow(page):\n    time.sleep(30)\n"
    root = project(tmp_path, {"test_slow": slow})
    with pytest.raises(ExecutionError, match="time limit"):
        ExecutionEngine(repo).execute(config(root, tmp_path, run_timeout_s=3))


@pytest.mark.whitebox
def test_a_collection_error_is_reported_not_swallowed(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, {"test_syntax": "def test_syntax(page)\n    pass\n"})
    with pytest.raises(ExecutionError):
        ExecutionEngine(repo).execute(config(root, tmp_path))


@pytest.mark.whitebox
def test_the_engine_needs_a_run_id(repo: InMemoryRepository, tmp_path: Path) -> None:
    set_run_id("")
    root = project(tmp_path, MIXED)
    with pytest.raises(PolicyError, match="run ID"):
        ExecutionEngine(repo).execute(config(root, tmp_path))


@pytest.mark.whitebox
def test_evidence_stays_inside_the_evidence_directory(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    root = project(tmp_path, MIXED)
    ExecutionEngine(repo).execute(config(root, tmp_path))
    evidence = (tmp_path / "evidence").resolve()
    for result in repo.list_results("run-1"):
        for name in (result.screenshot, result.dom_snapshot):
            if name:
                assert (evidence / name).resolve().is_relative_to(evidence)
    assert os.path.isdir(evidence)


@pytest.mark.blackbox
def test_the_projects_own_pytest_settings_do_not_leak_into_a_run(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    """Scripts often live inside the repository, whose pyproject sets markers and addopts."""
    parent = tmp_path / "workspace"
    parent.mkdir()
    (parent / "pytest.ini").write_text(
        "[pytest]\naddopts = --definitely-not-an-option\n", encoding="utf-8"
    )
    root = project(parent, {"test_pass": "def test_pass(page):\n    assert True\n"})
    summary = ExecutionEngine(repo).execute(config(root, tmp_path))
    assert summary.passed == 1
    assert repo.list_results("run-1")[0].tc_id == "TEST-PASS"
