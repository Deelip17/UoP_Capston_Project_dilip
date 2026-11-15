"""Builders for stored pipeline records, used by the reporting tests (FR-31 to FR-39).

A small, valid set of requirements, test cases, scripts, results, healing events,
analyses, audits and metric samples spread over a source run (analysis, generation,
scripting) and an execution run, with every number chosen so the expected metric
values can be written down by hand.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aitaf.core.models import (
    AnalyzedRequirement,
    FailureAnalysis,
    HealingEvent,
    LlmAudit,
    LocatorStrategy,
    MetricSample,
    ReviewStatus,
    RiskLevel,
    Run,
    RunStatus,
    Script,
    TestCase,
    TestResult,
)
from aitaf.core.storage import InMemoryRepository

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)
SOURCE = "run-src"
EXEC = "run-exec"


def run(run_id: str, provider: str = "mock") -> Run:
    return Run(
        run_id=run_id,
        started_at=NOW,
        finished_at=NOW,
        status=RunStatus.COMPLETED,
        provider=provider,
        environment="playwright headless, python 3.12",
    )


def requirement(req_id: str) -> AnalyzedRequirement:
    return AnalyzedRequirement(
        req_id=req_id,
        source_ref=f"shop.md#{req_id}",
        content_hash="h",
        risk=RiskLevel.MEDIUM,
        risk_rationale="why",
        prompt_version="ra-v1",
    )


def case(tc_id: str, req_id: str, status: ReviewStatus = ReviewStatus.APPROVED) -> TestCase:
    return TestCase(
        tc_id=tc_id,
        req_id=req_id,
        scenario_id=f"{req_id}-S1",
        title=f"Verify {tc_id}",
        steps=["open"],
        expected=["ok"],
        priority="M",
        review_status=status,
        model="mock-1",
        prompt_version="tg-v1",
    )


def script(tc_id: str) -> Script:
    return Script(
        script_id=f"SCR-{tc_id}",
        tc_id=tc_id,
        framework="playwright",
        path=f"tests/test_{tc_id.lower()}.py",
        validation_result="passed",
        model="mock-1",
        prompt_version="sg-v1",
    )


def result(tc_id: str, status: str, run_id: str = EXEC, **extra: object) -> TestResult:
    base: dict[str, object] = {
        "result_id": f"res-{tc_id}",
        "run_id": run_id,
        "tc_id": tc_id,
        "status": status,
        "duration_ms": 100,
        "log": "" if status == "passed" else f"{tc_id} failed",
        "nodeid": f"tests/test_{tc_id.lower()}.py::test_{tc_id.lower()}",
    }
    return TestResult(**{**base, **extra})  # type: ignore[arg-type]


def healing_event(event_id: str, step_ref: str, outcome: str) -> HealingEvent:
    proposed = outcome == "proposed"
    return HealingEvent(
        event_id=event_id,
        run_id=EXEC,
        step_ref=step_ref,
        loc_id="login.login_submit",
        old_strategy=LocatorStrategy(kind="id", value="login-button"),
        new_strategy=LocatorStrategy(kind="id", value="signin-btn") if proposed else None,
        strategy_used="similarity",
        confidence=0.8 if proposed else 0.0,
        validated=proposed,
        outcome=outcome,  # type: ignore[arg-type]
        duration_ms=4,
        created_at=NOW,
    )


def analysis(tc_id: str, category: str, source: str = "rules") -> FailureAnalysis:
    return FailureAnalysis(
        analysis_id=f"FA-res-{tc_id}",
        run_id=EXEC,
        result_id=f"res-{tc_id}",
        tc_id=tc_id,
        category=category,  # type: ignore[arg-type]
        root_cause=f"Cause for {tc_id}.",
        remediation=f"Next step for {tc_id}.",
        evidence_refs=[f"log:res-{tc_id}"],
        confidence=0.85,
        cluster_id="CL-0123abcd",
        source=source,  # type: ignore[arg-type]
        model="mock-1" if source == "llm" else None,
        prompt_version="fa-v1" if source == "llm" else None,
        created_at=NOW,
    )


def audit(call_id: str, run_id: str, mock: bool) -> LlmAudit:
    return LlmAudit(
        call_id=call_id,
        run_id=run_id,
        component="requirement_analyzer",
        provider="mock" if mock else "openai",
        model="mock-1" if mock else "gpt-test",
        prompt_version="ra-v1",
        tokens_in=1,
        tokens_out=1,
        input_hash="a" * 64,
        status="ok",
        mock=mock,
        created_at=NOW,
    )


def metric(
    run_id: str, component: str, operation: str, duration_ms: float, cost: float = 0.0
) -> MetricSample:
    return MetricSample(
        run_id=run_id,
        component=component,
        operation=operation,
        outcome="ok",
        detail="",
        duration_ms=duration_ms,
        tokens_in=0,
        tokens_out=0,
        cost_usd=cost,
        created_at=NOW,
    )


def seeded_repo(*, live: bool = False) -> InMemoryRepository:
    """Four requirements, four cases, four scripts and a mixed execution.

    * R1: two approved cases (TC-1 passes, TC-2 fails on a locator that was healed in
      vain); R2: one approved case (TC-3 errors); R3: a Pending case only (TC-4 never
      ran); R4: no case at all. Coverage 2 of 4 requirements.
    * Executed: TC-1 passed, TC-2 failed, TC-3 error, TC-5 skipped (no script).
    """
    repo = InMemoryRepository()
    repo.create_run(run(SOURCE))
    repo.create_run(run(EXEC))
    for req_id in ("R1", "R2", "R3", "R4"):
        repo.add_requirement(SOURCE, requirement(req_id))
    repo.add_test_case(SOURCE, case("TC-1", "R1"))
    repo.add_test_case(SOURCE, case("TC-2", "R1"))
    repo.add_test_case(SOURCE, case("TC-3", "R2"))
    repo.add_test_case(SOURCE, case("TC-4", "R3", ReviewStatus.PENDING))
    for tc_id in ("TC-1", "TC-2", "TC-3", "TC-4"):
        repo.add_script(SOURCE, script(tc_id))
    repo.add_result(result("TC-1", "passed", screenshot="a.png", dom_snapshot="a.html"))
    repo.add_result(
        result(
            "TC-2",
            "failed",
            screenshot="b.png",
            dom_snapshot="b.html",
            error_type="LookupError",
            error_text="no locator strategy matched for login_submit on page login",
        )
    )
    repo.add_result(result("TC-3", "error", error_type="RuntimeError", error_text="odd"))
    repo.add_result(result("TC-5", "skipped"))
    repo.add_healing_event(
        EXEC,
        healing_event("ev1", "tests/test_tc-2.py::test_tc-2#login.login_submit", "no_candidate"),
    )
    repo.add_healing_event(
        EXEC, healing_event("ev2", "tests/test_tc-2.py::test_tc-2#login.login_submit", "proposed")
    )
    repo.add_healing_event(
        EXEC, healing_event("ev3", "tests/test_tc-3.py::test_tc-3#login.other", "no_candidate")
    )
    repo.add_failure_analysis(EXEC, analysis("TC-2", "locator"))
    repo.add_failure_analysis(EXEC, analysis("TC-3", "unknown", source="llm"))
    repo.add_audit(audit("c1", SOURCE, mock=not live))
    repo.add_audit(audit("c2", EXEC, mock=not live))
    for component, operation, ms, cost in (
        ("requirement_analyzer", "analyze", 100.0, 0.001),
        ("test_case_generator", "generate", 300.0, 0.002),
        ("script_generator", "generate", 200.0, 0.001),
        ("llm_gateway", "requirement_analyzer", 90.0, 0.001),
    ):
        repo.add_metric(SOURCE, metric(SOURCE, component, operation, ms, cost))
    repo.add_metric(EXEC, metric(EXEC, "failure_analyzer", "analyze", 5.0, 0.0005))
    for ms in (10.0, 20.0, 30.0, 40.0, 50.0):
        repo.add_metric(EXEC, metric(EXEC, "reporting_engine", "render", ms))
    return repo
