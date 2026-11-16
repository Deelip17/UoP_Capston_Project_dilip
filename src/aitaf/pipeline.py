"""``aitaf run``: the whole pipeline in one command (FR-34, NFR-05, NFR-08).

Requirements text goes in; test cases, scripts, results, healing events, failure analyses,
a report and the dashboard come out, each stage being the same command a person would
type. The stages are run through ``stage`` (the CLI's own ``main``), so this module adds
no logic of its own beyond the order, the human-approval gate and the demo shop.

The human gate stays: without ``--approve-all`` the run stops after test-case generation
and says how to approve. ``--approve-all`` is a shortcut for demonstrations and
measurements; it is stated in the output and is not a review.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from aitaf.core.errors import ConfigError
from aitaf.core.models import ReviewStatus
from aitaf.core.storage import SqliteRepository
from aitaf.sampleapp import ShopServer

EXIT_OK = 0
EXIT_USAGE = 2
DEFAULT_PAGES = Path("data") / "dom" / "shop"

Stage = Callable[[list[str]], int]


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="path to the JSON configuration file")
    parser.add_argument("--input", required=True, help="requirements file (.txt, .md)")
    parser.add_argument("--db", default="aitaf.db", help="SQLite database path")
    parser.add_argument(
        "--out-dir", default="reports/pipeline", help="scripts, evidence, dashboard"
    )
    parser.add_argument(
        "--demo-shop", action="store_true", help="start the sample shop (open login)"
    )
    parser.add_argument("--base-url", help="system under test (when not using --demo-shop)")
    parser.add_argument("--allow-host", action="append", default=[], help="host the run may target")
    parser.add_argument(
        "--mutation", action="append", default=[], metavar="ID", help="change the demo shop"
    )
    parser.add_argument("--approve-all", action="store_true", help="approve every test case itself")
    parser.add_argument("--heal", action="store_true", help="heal locator failures while executing")
    parser.add_argument(
        "--pages", metavar="DIR", help="baseline page snapshots (demo shop default)"
    )
    parser.add_argument("--labels", help="CSV tc_id,category for classification accuracy")
    parser.add_argument("--framework", choices=["playwright", "selenium"], default="playwright")
    parser.add_argument("--timeout-ms", type=int, default=5000, help="default action timeout")
    parser.add_argument("--no-dashboard", action="store_true", help="skip the dashboard")


def _approve_all(db: str) -> int:
    repo = SqliteRepository(db)
    try:
        run_id = repo.latest_run_with_requirements()
        if run_id is None:
            return 0
        cases = repo.list_test_cases(run_id)
        for case in cases:
            repo.set_review_status(run_id, case.tc_id, ReviewStatus.APPROVED)
        return len(cases)
    finally:
        repo.close()


def run_pipeline(args: argparse.Namespace, stage: Stage) -> int:
    """Run every stage in order; 0 when the pipeline completed (failing tests are results)."""
    if not args.demo_shop and not args.base_url:
        raise ConfigError("give --demo-shop or --base-url (the system under test)")
    out = Path(args.out_dir)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    scripts, evidence = out / "scripts", out / "runs"
    config = ["--config", args.config] if args.config else []
    pages = args.pages or (str(DEFAULT_PAGES) if args.demo_shop else None)
    db = ["--db", args.db]

    def step(name: str, *argv: str, ok: tuple[int, ...] = (0,)) -> int:
        print(f"\n== {name}")
        code = stage([name, *config, *argv])
        if code not in ok:
            print(f"aitaf run: stopped, '{name}' exited with {code}")
            return code
        return EXIT_OK

    first: list[tuple[str, list[str], tuple[int, ...]]] = [
        ("analyze", ["--input", args.input, *db], (0,)),
        ("generate", [*db], (0,)),
    ]
    for name, argv, ok in first:
        if (code := step(name, *argv, ok=ok)) != EXIT_OK:
            return code
    if not args.approve_all:
        print("\nstopped at the human gate: review the test cases, then approve them with")
        print(f"  aitaf review --db {args.db} --approve TC_ID")
        print("or run again with --approve-all (a demonstration shortcut, not a review)")
        return EXIT_OK
    print(
        f"\napproval: {_approve_all(args.db)} test case(s) approved automatically (--approve-all)"
    )

    try:
        shop = ShopServer(mutations=args.mutation, open_login=True) if args.demo_shop else None
    except KeyError as exc:
        raise ConfigError(f"unknown mutation: {exc.args[0]}") from exc
    try:
        if shop is not None:
            shop.start()
        url = shop.url if shop is not None else str(args.base_url)
        hosts = [item for host in args.allow_host for item in ("--allow-host", host)]
        script = [*db, "--out-dir", str(scripts), "--no-review", "--base-url", url, *hosts]
        script += ["--framework", args.framework, *(["--pages", pages] if pages else [])]
        execute = ["--scripts", str(scripts), "--base-url", url, *db, *hosts]
        execute += ["--evidence", str(evidence), "--timeout-ms", str(args.timeout_ms)]
        if args.heal:
            execute += ["--heal", *(["--baseline", pages] if pages else [])]
        second: list[tuple[str, list[str], tuple[int, ...]]] = [
            ("script", script, (0,)),
            ("execute", execute, (0, 1)),
        ]
        for name, argv, ok in second:
            if (code := step(name, *argv, ok=ok)) != EXIT_OK:
                return code
    finally:
        if shop is not None:
            shop.stop()

    labels = ["--labels", args.labels] if args.labels else []
    for name, argv in (
        ("diagnose", [*db, "--evidence", str(evidence)]),
        ("report", [*db, "--evidence", str(evidence), *labels]),
    ):
        if (code := step(name, *argv)) != EXIT_OK:
            return code
    if not args.no_dashboard:
        step("dashboard", *db, "--out", str(out / "dashboard"), *labels)
    print(f"\npipeline finished; output in {out}")
    return EXIT_OK
