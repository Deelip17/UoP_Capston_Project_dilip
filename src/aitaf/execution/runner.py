"""The Execution Engine: run generated scripts with PyTest and store the results.

Flow (FR-17 to FR-21, NFR-04, NFR-11, NFR-23):

1. the base URL is checked against the allow-list **before anything starts** (FR-21);
2. PyTest runs in a subprocess with the engine's plugin, optionally with parallel
   workers (pytest-xdist) and a hard time limit; failing tests are rerun up to
   ``retries`` times and the attempt count is recorded (FR-20);
3. the plugin's result lines are read back, failure text is masked, and one
   :class:`~aitaf.core.models.TestResult` per test is stored with its screenshot and
   DOM snapshot links (FR-18, FR-19).

The subprocess gets a copy of the environment without anything that looks like a
secret, so generated tests never see the API key (NFR-11). The engine does not call
the Self-Healing Engine yet; that integration is a later slice.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import aitaf
from aitaf.core.errors import ExecutionError, PolicyError
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import mask
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import TestResult
from aitaf.core.storage import Repository
from aitaf.execution.allowlist import check_base_url
from aitaf.execution.config import RunConfig

_log = get_logger(__name__)
_SECRET_NAME = re.compile(
    r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|^(OPENAI|ANTHROPIC|AWS|AZURE|GITHUB)_", re.I
)
_PYTEST_FAILURES = 1  # exit code: some tests failed (not an engine error)
_PYTEST_NO_TESTS = 5


@dataclass(frozen=True)
class ExecutedTest:
    """The final state of one test after all attempts."""

    tc_id: str
    nodeid: str
    status: str
    duration_ms: int
    attempts: int
    screenshot: str
    dom_snapshot: str
    log: str


@dataclass
class RunSummary:
    """Outcome of one execution run."""

    run_id: str
    environment: str
    executed: list[ExecutedTest] = field(default_factory=list)
    duration_ms: int = 0
    junit_path: Path = Path()

    def _count(self, status: str) -> int:
        return sum(1 for test in self.executed if test.status == status)

    @property
    def passed(self) -> int:
        return self._count("passed")

    @property
    def failed(self) -> int:
        return self._count("failed")

    @property
    def errors(self) -> int:
        return self._count("error")

    @property
    def skipped(self) -> int:
        return self._count("skipped")

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0


def clean_environment(environ: dict[str, str]) -> dict[str, str]:
    """A copy of ``environ`` without names that look like secrets (NFR-11)."""
    return {name: value for name, value in environ.items() if not _SECRET_NAME.search(name)}


def describe_environment(config: RunConfig) -> str:
    """Environment text stored with the run (FR-19)."""
    mode = "headless" if config.headless else "headed"
    return (
        f"{config.driver} {mode}, python {platform.python_version()}, "
        f"{platform.system()} {platform.release()}, workers {config.workers}, "
        f"timeout {config.timeout_ms} ms, retries {config.retries}"
    )


def _tc_ids(scripts_dir: Path) -> dict[str, str]:
    """Map script path (as PyTest reports it) to the test case ID from the manifest."""
    manifest = scripts_dir / "manifest.json"
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        return {str(e["path"]): str(e["tc_id"]) for e in entries if "path" in e and "tc_id" in e}
    except (OSError, ValueError, TypeError, KeyError):
        return {}


def _fallback_tc_id(nodeid: str) -> str:
    name = nodeid.split("::")[-1]
    name = name[5:] if name.startswith("test_") else name
    return re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper() or "TEST"


class ExecutionEngine:
    """Run a script directory and persist the results of the current run."""

    def __init__(
        self, repo: Repository, metrics: Metrics | None = None, python: str = sys.executable
    ) -> None:
        self._repo = repo
        self._metrics = metrics
        self._python = python

    def execute(self, config: RunConfig) -> RunSummary:
        run_id = current_run_id()
        if not run_id:
            raise PolicyError("no run ID is set; start a run before executing tests")
        check_base_url(config.base_url, config.allowed_hosts)  # FR-21: before any process starts
        scripts = config.scripts_dir
        if not scripts.is_dir():
            raise ExecutionError(f"scripts directory not found: {scripts.name}")
        if not any((scripts / "tests").glob("test_*.py")) and not any(scripts.glob("test_*.py")):
            raise ExecutionError("no test files found in the scripts directory")

        config.evidence_dir.mkdir(parents=True, exist_ok=True)
        summary = RunSummary(run_id=run_id, environment=describe_environment(config))
        results_dir = config.evidence_dir / "results"
        # An empty config file keeps the project's own PyTest settings (markers, addopts) out
        # of the run, so test IDs are relative to the scripts directory.
        (config.evidence_dir / "pytest_engine.ini").write_text("[pytest]\n", encoding="utf-8")
        for stale in results_dir.glob("*.jsonl"):
            stale.unlink()

        with timed(self._metrics, "execution_engine", "run"):
            targets: list[str] = ["tests" if (scripts / "tests").is_dir() else "."]
            for attempt in range(1, config.retries + 2):
                self._run_pytest(config, targets, attempt, summary)
                latest = self._collect(config)
                failing = [n for n, rec in latest.items() if rec["outcome"] in ("failed", "error")]
                if not failing or attempt > config.retries:
                    break
                targets = sorted(failing)
                _log.info("retrying %d failing test(s), attempt %d", len(failing), attempt + 1)

        manifest = _tc_ids(scripts)
        for nodeid, record in sorted(latest.items()):
            path = nodeid.split("::")[0]
            tc_id = manifest.get(path) or _fallback_tc_id(nodeid)
            log = mask(str(record["message"])).text if record["message"] else ""
            executed = ExecutedTest(
                tc_id=tc_id,
                nodeid=nodeid,
                status=str(record["outcome"]),
                duration_ms=max(0, round(float(record["duration_s"]) * 1000)),  # type: ignore[arg-type]
                attempts=int(record["attempts"]),  # type: ignore[call-overload]
                screenshot=str(record["screenshot"]),
                dom_snapshot=str(record["dom"]),
                log=log,
            )
            summary.executed.append(executed)
            self._repo.add_result(
                TestResult(
                    result_id=uuid.uuid4().hex,
                    run_id=run_id,
                    tc_id=executed.tc_id,
                    status=executed.status,  # type: ignore[arg-type]
                    duration_ms=executed.duration_ms,
                    log=executed.log,
                    attempts=executed.attempts,
                    screenshot=executed.screenshot,
                    dom_snapshot=executed.dom_snapshot,
                )
            )
        summary.duration_ms = sum(test.duration_ms for test in summary.executed)
        summary.junit_path = config.evidence_dir / f"junit_attempt{attempt}.xml"
        return summary

    # ------------------------------------------------------------------ pytest

    def _run_pytest(
        self, config: RunConfig, targets: list[str], attempt: int, summary: RunSummary
    ) -> None:
        evidence = config.evidence_dir
        command = [
            self._python,
            "-m",
            "pytest",
            "-p",
            "aitaf.execution.plugin",
            "-p",
            "no:cacheprovider",
            "-c",
            str(evidence / "pytest_engine.ini"),
            "--rootdir",
            str(config.scripts_dir),
            "-q",
            "--no-header",
            "--base-url",
            config.base_url,
            "--aitaf-results",
            str(evidence / "results"),
            "--aitaf-evidence",
            str(evidence),
            "--aitaf-attempt",
            str(attempt),
            "--aitaf-timeout-ms",
            str(config.timeout_ms),
            "--aitaf-allowed-hosts",
            ",".join(config.allowed_hosts),
            "--junitxml",
            str(evidence / f"junit_attempt{attempt}.xml"),
        ]
        if not config.headless:
            command.append("--aitaf-headed")
        if config.checkpoints:
            command.append("--aitaf-checkpoints")
        if config.workers > 1:
            command += ["-n", str(config.workers)]
        command += targets

        env = clean_environment(dict(os.environ))
        package_root = str(Path(aitaf.__file__).resolve().parent.parent)
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [package_root, env.get("PYTHONPATH", "")]))
        try:
            done = subprocess.run(  # noqa: S603 - fixed argument list, no shell
                command,
                cwd=config.scripts_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=config.run_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ExecutionError(
                f"the run exceeded the time limit of {config.run_timeout_s} s and was stopped"
            ) from None
        if done.returncode == _PYTEST_NO_TESTS:
            raise ExecutionError("PyTest collected no tests in the scripts directory")
        if done.returncode > _PYTEST_FAILURES:
            tail = mask((done.stdout + done.stderr)[-800:]).text.strip()
            raise ExecutionError(
                f"PyTest could not run the scripts (exit {done.returncode}): {tail}"
            )

    def _collect(self, config: RunConfig) -> dict[str, dict[str, object]]:
        """Latest record per test across all attempts; attempts = highest attempt seen."""
        latest: dict[str, dict[str, object]] = {}
        for file in sorted((config.evidence_dir / "results").glob("*.jsonl")):
            for text in file.read_text(encoding="utf-8").splitlines():
                try:
                    line = json.loads(text)
                except ValueError:
                    continue
                nodeid = str(line["nodeid"]).replace("\\", "/")
                previous = latest.get(nodeid)
                key = (int(line["attempt"]), 1 if line["when"] == "teardown" else 0)
                if previous is None or key >= previous["_key"]:  # type: ignore[operator]
                    latest[nodeid] = {**line, "_key": key, "attempts": int(line["attempt"])}
        for record in latest.values():
            record.pop("_key", None)
        return latest
