"""The Execution Engine: run generated scripts with PyTest and store the results.

Flow (FR-17 to FR-21, NFR-04, NFR-11, NFR-23; FR-22 to FR-26 for healing):

1. the base URL is checked against the allow-list **before anything starts** (FR-21);
2. PyTest runs in a subprocess with the engine's plugin, optionally with parallel
   workers (pytest-xdist) and a hard time limit (FR-20);
3. a test that failed because no locator matched (``LookupError`` from the page
   object) is offered to the healer through the ``LocatorHealer`` interface of
   ``core``; if it proposes a new locator, the engine applies it to a **temporary
   copy** of the scripts and reruns that test there. The original scripts and the
   locator repository are never changed: a permanent change needs human approval
   (FR-25);
4. other failures are retried up to ``retries`` times; attempt counts are recorded;
5. one :class:`~aitaf.core.models.TestResult` per test is stored with masked failure
   text and links to its screenshot and DOM snapshot (FR-18, FR-19).

The subprocess gets a copy of the environment without anything that looks like a
secret, so generated tests never see the API key (NFR-11).
"""

from __future__ import annotations

import ast
import json
import os
import platform
import pprint
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import aitaf
from aitaf.core.errors import ExecutionError, PolicyError
from aitaf.core.healing import ElementSignature, FailureContext, HealStatus, LocatorHealer
from aitaf.core.logging import current_run_id, get_logger
from aitaf.core.masking import mask
from aitaf.core.metrics import Metrics, timed
from aitaf.core.models import Locator, LocatorStrategy, TestResult
from aitaf.core.storage import Repository
from aitaf.execution.allowlist import check_base_url
from aitaf.execution.config import RunConfig

_log = get_logger(__name__)
_SECRET_NAME = re.compile(
    r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|^(OPENAI|ANTHROPIC|AWS|AZURE|GITHUB)_", re.IGNORECASE
)
_LOCATOR_MISS = re.compile(r"no locator strategy matched for (\w+) on page (\w+)")
_PYTEST_FAILURES = 1  # exit code: some tests failed (not an engine error)
_PYTEST_NO_TESTS = 5
_KINDS = ("id", "css", "xpath", "text", "role", "attr")

BaselineLookup = Callable[[Locator], ElementSignature | None]


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
    healed: tuple[str, ...] = ()
    error_type: str = ""
    error_text: str = ""


@dataclass
class RunSummary:
    """Outcome of one execution run."""

    run_id: str
    environment: str
    executed: list[ExecutedTest] = field(default_factory=list)
    duration_ms: int = 0
    junit_path: Path = Path()
    heal_attempts: int = 0

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
    def healed(self) -> int:
        """Tests that passed after a healed locator was applied."""
        return sum(1 for t in self.executed if t.healed and t.status == "passed")

    @property
    def healing_success_rate(self) -> float | None:
        """Healed tests divided by healing requests; None if healing was never asked."""
        return self.healed / self.heal_attempts if self.heal_attempts else None

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0


def clean_environment(environ: dict[str, str]) -> dict[str, str]:
    """A copy of ``environ`` without names that look like secrets (NFR-11)."""
    return {name: value for name, value in environ.items() if not _SECRET_NAME.search(name)}


def describe_environment(config: RunConfig) -> str:
    """Environment text stored with the run (FR-19)."""
    mode = "headless" if config.headless else "headed"
    healing = ", healing on" if config.healing else ""
    return (
        f"{config.driver} {mode}, python {platform.python_version()}, "
        f"{platform.system()} {platform.release()}, workers {config.workers}, "
        f"timeout {config.timeout_ms} ms, retries {config.retries}{healing}"
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


def _as_strategy(pair: object) -> LocatorStrategy | None:
    if (
        isinstance(pair, tuple | list)
        and len(pair) == 2
        and all(isinstance(part, str) for part in pair)
        and pair[0] in _KINDS
        and pair[1]
    ):
        return LocatorStrategy(kind=pair[0], value=pair[1])
    return None


def read_locator_module(path: Path) -> dict[str, dict[str, object]] | None:
    """Parse a generated ``LOCATORS = {...}`` literal without executing the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "LOCATORS"
            ):
                value = ast.literal_eval(node.value)
                return value if isinstance(value, dict) else None
    except (OSError, SyntaxError, ValueError):
        return None
    return None


def apply_strategy(
    scripts_dir: Path, page: str, name: str, strategy: LocatorStrategy, *, permanent: bool = False
) -> bool:
    """Make ``strategy`` the primary locator of ``name`` in a scripts folder; keep the old one.

    Returns False when the locator file or the name is not there. ``permanent`` is for a
    change a person approved; the default marks the file as a one-run healed copy.
    """
    path = scripts_dir / "locators" / f"{page}_locators.py"
    module = read_locator_module(path)
    if module is None or name not in module:
        return False
    current = module[name]
    new = (strategy.kind, strategy.value)
    fallbacks = current.get("fallbacks", [])
    old = [current["primary"], *(fallbacks if isinstance(fallbacks, list) else [])]
    current["primary"] = new
    current["fallbacks"] = [pair for pair in old if tuple(pair) != new]
    note = "approved locator update" if permanent else "healed copy, one run, needs approval"
    path.write_text(
        f'"""Locator repository for {page!r}: {note}."""\n\n'
        f"LOCATORS = {pprint.pformat(module, sort_dicts=False)}\n",
        encoding="utf-8",
    )
    return True


def _locator_from(page: str, name: str, entry: object) -> Locator | None:
    if not isinstance(entry, dict):
        return None
    primary = _as_strategy(entry.get("primary"))
    fallbacks = [_as_strategy(item) for item in entry.get("fallbacks", [])]
    if primary is None or any(item is None for item in fallbacks):
        return None
    return Locator(
        loc_id=f"{page}.{name}",
        page=page,
        name=name,
        primary=primary,
        fallbacks=[item for item in fallbacks if item is not None],
        model="n/a",
        prompt_version="n/a",
    )


class ExecutionEngine:
    """Run a script directory and persist the results of the current run."""

    def __init__(
        self,
        repo: Repository,
        metrics: Metrics | None = None,
        python: str = sys.executable,
        healer: LocatorHealer | None = None,
        baseline: BaselineLookup | None = None,
    ) -> None:
        self._repo = repo
        self._metrics = metrics
        self._python = python
        self._healer = healer
        self._baseline = baseline

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
        # An empty config file keeps the project's own PyTest settings (markers, addopts) out
        # of the run, so test IDs are relative to the scripts directory.
        (config.evidence_dir / "pytest_engine.ini").write_text("[pytest]\n", encoding="utf-8")
        for stale in (config.evidence_dir / "results").glob("*.jsonl"):
            stale.unlink()

        healing_on = self._healer is not None and config.healing
        work_dir = scripts
        healed_notes: dict[str, list[str]] = {}
        attempt = 0
        heal_passes = 0
        retries_left = config.retries
        targets: list[str] = ["tests" if (scripts / "tests").is_dir() else "."]
        with timed(self._metrics, "execution_engine", "run"):
            while True:
                attempt += 1
                self._run_pytest(config, work_dir, targets, attempt)
                latest = self._collect(config)
                failing = sorted(
                    n for n, r in latest.items() if r["outcome"] in ("failed", "error")
                )
                if not failing:
                    break
                if healing_on and heal_passes < config.max_heal_passes:
                    rerun = self._heal(config, work_dir, latest, failing, healed_notes, summary)
                    if rerun is not None:
                        heal_passes += 1
                        work_dir, targets = rerun
                        continue
                if retries_left == 0:
                    break
                retries_left -= 1
                targets = failing
                _log.info("retrying %d failing test(s), attempt %d", len(failing), attempt + 1)

        manifest = _tc_ids(scripts)
        for nodeid, record in sorted(latest.items()):
            tc_id = manifest.get(nodeid.split("::")[0]) or _fallback_tc_id(nodeid)
            notes = healed_notes.get(nodeid, [])
            text = mask(str(record["message"])).text if record["message"] else ""
            log = ("; ".join(notes) + ("\n" if text else "")) + text if notes else text
            executed = ExecutedTest(
                tc_id=tc_id,
                nodeid=nodeid,
                status=str(record["outcome"]),
                duration_ms=max(0, round(float(record["duration_s"]) * 1000)),  # type: ignore[arg-type]
                attempts=int(record["attempts"]),  # type: ignore[call-overload]
                screenshot=str(record["screenshot"]),
                dom_snapshot=str(record["dom"]),
                log=log,
                healed=tuple(notes),
                error_type=str(record.get("error_type", "")),
                error_text=mask(str(record.get("error_text", ""))).text,
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
                    nodeid=executed.nodeid,
                    error_type=executed.error_type,
                    error_text=executed.error_text,
                )
            )
        summary.duration_ms = sum(test.duration_ms for test in summary.executed)
        summary.junit_path = config.evidence_dir / f"junit_attempt{attempt}.xml"
        return summary

    # ----------------------------------------------------------------- healing

    def _heal(
        self,
        config: RunConfig,
        work_dir: Path,
        latest: dict[str, dict[str, object]],
        failing: list[str],
        notes: dict[str, list[str]],
        summary: RunSummary,
    ) -> tuple[Path, list[str]] | None:
        """Ask the healer about each locator failure; return (copy, tests to rerun) or None."""
        assert self._healer is not None
        proposals: list[tuple[str, str, str, LocatorStrategy, float]] = []
        decided: dict[
            tuple[str, str], tuple[LocatorStrategy, float]
        ] = {}  # one question per locator
        for nodeid in failing:
            record = latest[nodeid]
            miss = _LOCATOR_MISS.search(str(record.get("error_text", "")))
            if miss is None:
                continue
            name, page = miss.group(1), miss.group(2)
            if (page, name) in decided:
                strategy, confidence = decided[(page, name)]
                proposals.append((nodeid, page, name, strategy, confidence))
                continue
            module = read_locator_module(work_dir / "locators" / f"{page}_locators.py")
            locator = _locator_from(page, name, (module or {}).get(name))
            dom = self._read_dom(config, str(record.get("dom", "")))
            if locator is None or dom is None:
                _log.info("cannot heal %s: locator or DOM snapshot unavailable", nodeid)
                continue
            baseline = self._baseline(locator) if self._baseline else None
            summary.heal_attempts += 1
            result = self._healer.heal(
                FailureContext(
                    step_ref=f"{nodeid}#{locator.loc_id}",
                    action="locate",
                    locator=locator,
                    error_type=str(record.get("error_type", "")),
                    error_message=str(record.get("error_text", "")),
                    dom_html=dom,
                    baseline=baseline,
                )
            )
            if result.status is HealStatus.HEALED and result.strategy is not None:
                decided[(page, name)] = (result.strategy, result.confidence)
                proposals.append((nodeid, page, name, result.strategy, result.confidence))
        if not proposals:
            return None

        healed_dir = config.evidence_dir / "healed_scripts"
        if work_dir == config.scripts_dir:
            shutil.rmtree(healed_dir, ignore_errors=True)
            shutil.copytree(
                config.scripts_dir,
                healed_dir,
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
            )
        for nodeid, page, name, strategy, confidence in proposals:
            self._patch(healed_dir, page, name, strategy)
            notes.setdefault(nodeid, []).append(
                f"healed {page}.{name} -> {strategy.kind}={strategy.value} "
                f"(confidence {confidence:.2f}, proposed, needs approval)"
            )
        return healed_dir, sorted({nodeid for nodeid, *_ in proposals})

    @staticmethod
    def _read_dom(config: RunConfig, name: str) -> str | None:
        if not name or Path(name).name != name:
            return None
        try:
            return (config.evidence_dir / name).read_text(encoding="utf-8")
        except OSError:
            return None

    @staticmethod
    def _patch(healed_dir: Path, page: str, name: str, strategy: LocatorStrategy) -> None:
        """Make ``strategy`` the primary locator of ``name`` in the temporary copy only."""
        apply_strategy(healed_dir, page, name, strategy)

    # ------------------------------------------------------------------ pytest

    def _run_pytest(self, config: RunConfig, cwd: Path, targets: list[str], attempt: int) -> None:
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
            str(cwd),
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
                cwd=cwd,
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
