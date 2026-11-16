"""Generation evaluation: do generated scripts run on the real application? (objective O2)

Requirements: FR-12, FR-14, FR-16, NFR-02.
The pipeline (analyze, generate, approve, script) runs through the command line in a
fresh database, once per configuration: the old prompt without page context (``sg-v1``)
and the new one with the page catalogue (``sg-v2``), on the mock provider or a live model.
Every generated script is then run in Chromium against the unmutated shop with sign-in
open, so a result does not depend on a password. The test cases are approved by the
harness; a person would review them (stated in the report).

Executable means the script ran its steps without a missing element or a runtime error:
it passed, or it reached an assertion and the assertion failed. A script that failed with
a locator or runtime error counts as not executable. The pass rate is reported as well.
"""

from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from aitaf.core.models import ReviewStatus
from aitaf.core.storage import SqliteRepository
from aitaf.sampleapp import ShopServer
from aitaf.scriptgen import PageCatalogue

SCRIPT_COMPONENTS = ("script_generator",)
_SUMMARY = re.compile(r"summary: (\d+) scripts written .*?(\d+) rejected, (\d+) locators")
_EXECUTABLE_ERRORS = ("AssertionError",)


@dataclass(frozen=True)
class GenerationTrial:
    """One configuration of the pipeline and what its scripts did on the shop."""

    config: str
    provider: str  # mock or live
    page_context: bool
    cases: int
    scripts: int
    rejected: int
    locators: int
    valid_locators: int
    passed: int
    failed: int
    errors: int
    executable: int
    llm_calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    generation_s: float
    script_step_s: float


COLUMNS = tuple(f.name for f in fields(GenerationTrial))


def _run(
    args: Sequence[str], env: Mapping[str, str], cwd: Path, ok_codes: tuple[int, ...] = (0,)
) -> str:
    done = subprocess.run(
        [sys.executable, "-m", "aitaf", *args],
        capture_output=True,
        text=True,
        env=dict(env),
        cwd=cwd,
        check=False,
    )
    if done.returncode not in ok_codes:
        raise RuntimeError(f"aitaf {args[0]} failed: {(done.stderr or done.stdout)[-300:]}")
    return done.stdout


def _valid_locators(scripts_dir: Path, catalogue: PageCatalogue) -> tuple[int, int]:
    """(primary locators in the generated repository, those that exist on the pages)."""
    known = {s for e in catalogue.elements() for s in e.strategies()}
    total = valid = 0
    for path in (scripts_dir / "locators").glob("*_locators.py"):
        namespace: dict[str, object] = {}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)  # noqa: S102
        for entry in dict(namespace.get("LOCATORS", {})).values():  # type: ignore[call-overload]
            total += 1
            valid += tuple(entry["primary"]) in known
    return total, valid


def run_generation_trial(
    config: str,
    *,
    pages_dir: Path | str | None,
    requirements: Path | str,
    live: bool,
    cap: int = 300,
    cache_dir: Path | str | None = None,
    repo_root: Path | str = ".",
    keep_db: Path | str | None = None,
) -> GenerationTrial:
    """Run the pipeline for one configuration and execute its scripts in Chromium."""
    root = Path(repo_root).resolve()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["LLM_PROVIDER"] = "openai" if live else "mock"
    env["LLM_CALL_CAP"] = str(cap)
    if cache_dir:
        env["LLM_CACHE_DIR"] = str(Path(cache_dir).resolve())
    if not live:
        env.pop("OPENAI_API_KEY", None)
        for name in ("LLM_PRICE_IN_PER_1K", "LLM_PRICE_OUT_PER_1K"):
            env.pop(name, None)  # a mock call costs nothing, whatever the price settings
    pages = Path(pages_dir).resolve() if pages_dir else None
    req = str(Path(requirements).resolve())
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        db = str(work / "eval.db")
        started = time.perf_counter()
        _run(["analyze", "--input", req, "--db", db], env, root)
        _run(["generate", "--db", db], env, root)
        repo = SqliteRepository(db)
        try:
            run_id = repo.latest_run_with_requirements()
            assert run_id is not None
            cases = repo.list_test_cases(run_id)
            for case in cases:
                repo.set_review_status(run_id, case.tc_id, ReviewStatus.APPROVED)
        finally:
            repo.close()
        step = time.perf_counter()
        script_args = ["script", "--db", db, "--out-dir", str(work / "gen"), "--no-review"]
        with ShopServer(open_login=True) as shop:
            out = _run(
                [*script_args, "--base-url", shop.url, *(["--pages", str(pages)] if pages else [])],
                env,
                root,
            )
            script_step = time.perf_counter() - step
            generation = time.perf_counter() - started
            match = _SUMMARY.search(out)
            scripts, rejected, locators = (int(g) for g in match.groups()) if match else (0, 0, 0)
            _run(
                [
                    "execute",
                    "--scripts",
                    str(work / "gen"),
                    "--base-url",
                    shop.url,
                    "--db",
                    db,
                    "--evidence",
                    str(work / "runs"),
                    "--timeout-ms",
                    "5000",
                ],
                env,
                root,
                ok_codes=(0, 1),
            )
        catalogue = PageCatalogue.from_snapshots(pages or root / "data" / "dom" / "shop")
        total_loc, valid_loc = _valid_locators(work / "gen", catalogue) if scripts else (0, 0)
        repo = SqliteRepository(db)
        try:
            exec_run = repo.latest_run_with_results()
            results = repo.list_results(exec_run) if exec_run else []
            audits = [a for r in (run_id, exec_run) if r for a in repo.list_audits(r)]
            samples = [s for r in (run_id, exec_run) if r for s in repo.list_metrics(r)]
        finally:
            repo.close()
        if keep_db:
            Path(keep_db).parent.mkdir(parents=True, exist_ok=True)
            Path(keep_db).write_bytes(Path(db).read_bytes())
    passed = sum(r.status == "passed" for r in results)
    failed = sum(r.status == "failed" for r in results)
    errors = sum(r.status == "error" for r in results)
    executable = passed + sum(
        r.status == "failed" and r.error_type in _EXECUTABLE_ERRORS for r in results
    )
    return GenerationTrial(
        config=config,
        provider="live" if live else "mock",
        page_context=pages is not None,
        cases=len(cases),
        scripts=scripts,
        rejected=rejected,
        locators=total_loc if scripts else locators,
        valid_locators=valid_loc,
        passed=passed,
        failed=failed,
        errors=errors,
        executable=executable,
        llm_calls=len(audits),
        tokens_in=sum(a.tokens_in for a in audits),
        tokens_out=sum(a.tokens_out for a in audits),
        cost_usd=round(sum(s.cost_usd for s in samples), 6),
        generation_s=round(generation, 2),
        script_step_s=round(script_step, 2),
    )


def write_generation_csv(trials: Sequence[GenerationTrial], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for trial in trials:
            writer.writerow(asdict(trial))
    return target


def read_generation_csv(path: Path | str) -> list[GenerationTrial]:
    ints = {f.name for f in fields(GenerationTrial) if f.type == "int"}
    floats = {f.name for f in fields(GenerationTrial) if f.type == "float"}
    out = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            data: dict[str, object] = {}
            for key, value in row.items():
                if key in ints:
                    data[key] = int(value)
                elif key in floats:
                    data[key] = float(value)
                elif key == "page_context":
                    data[key] = value == "True"
                else:
                    data[key] = value
            out.append(GenerationTrial(**data))  # type: ignore[arg-type]
    return out
