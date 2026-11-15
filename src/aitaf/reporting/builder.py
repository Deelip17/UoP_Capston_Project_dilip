"""Build the report data model from stored records (FR-31, FR-34, FR-39).

Two runs are involved: the **execution run** (results, healing events, failure
analyses) and the **source run** that analysed requirements, generated test cases and
wrote the scripts. The builder joins them by test case ID into one traceable chain.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from aitaf.core.errors import PersistenceError
from aitaf.core.models import FailureAnalysis, HealingEvent
from aitaf.core.storage import Repository
from aitaf.reporting.metrics import compute_metrics, provider_label
from aitaf.reporting.model import ReportData, ReportTest, TraceRow


def _healed(nodeid: str, events: list[HealingEvent]) -> bool:
    return bool(nodeid) and any(
        e.outcome == "proposed" and e.step_ref.startswith(nodeid + "#") for e in events
    )


def build_report(
    repo: Repository,
    run_id: str,
    source_run_id: str | None = None,
    *,
    labels: Mapping[str, str] | None = None,
    title: str = "AITAF test run report",
) -> ReportData:
    """Collect everything one report shows (source run defaults to the latest analysis run)."""
    run = repo.get_run(run_id)
    if run is None:
        raise PersistenceError(f"unknown run: {run_id!r}")
    source = source_run_id or repo.latest_run_with_requirements()
    if source == run_id:
        source = None

    requirements = {r.req_id: r for r in repo.list_requirements(source)} if source else {}
    cases = {c.tc_id: c for c in repo.list_test_cases(source)} if source else {}
    scripts = {s.tc_id: s for s in repo.list_scripts(source)} if source else {}
    events = repo.list_healing_events(run_id)
    analyses: list[FailureAnalysis] = repo.list_failure_analyses(run_id)
    by_result = {a.result_id: a for a in analyses}

    tests: list[ReportTest] = []
    trace: list[TraceRow] = []
    for result in repo.list_results(run_id):
        case = cases.get(result.tc_id)
        script = scripts.get(result.tc_id)
        analysis = by_result.get(result.result_id)
        req_id = case.req_id if case else ""
        requirement = requirements.get(req_id)
        tests.append(
            ReportTest(
                result_id=result.result_id,
                tc_id=result.tc_id,
                title=case.title if case else result.tc_id,
                requirement_id=req_id,
                script_path=script.path if script else "",
                status=result.status,
                duration_ms=result.duration_ms,
                attempts=result.attempts,
                healed=_healed(result.nodeid, events),
                screenshot=result.screenshot,
                dom_snapshot=result.dom_snapshot,
                log=result.log,
                analysis=analysis,
            )
        )
        trace.append(
            TraceRow(
                result_id=result.result_id,
                tc_id=result.tc_id,
                requirement_id=req_id,
                requirement_ref=requirement.source_ref if requirement else "",
                script_path=script.path if script else "",
                status=result.status,
                analysis_category=analysis.category if analysis else "",
                cluster_id=analysis.cluster_id if analysis else "",
            )
        )

    clusters: dict[str, list[str]] = {}
    for analysis in analyses:
        clusters.setdefault(analysis.cluster_id, []).append(analysis.tc_id)
    runs = [run_id] if source is None else [source, run_id]
    return ReportData(
        title=title,
        run=run,
        source_run_id=source,
        generated_at=datetime.now(UTC),
        provider=provider_label(repo, runs),
        tests=tests,
        healing_events=events,
        analyses=analyses,
        clusters=clusters,
        metrics=compute_metrics(repo, run_id, source, labels),
        trace=trace,
    )


def trace_for_result(data: ReportData, result_id: str) -> TraceRow | None:
    """The full chain for one test result, or None if the result is not in the report."""
    return next((row for row in data.trace if row.result_id == result_id), None)


def trace_for_requirement(data: ReportData, requirement_id: str) -> list[TraceRow]:
    """Every executed test that traces back to a requirement (the reverse query)."""
    return [row for row in data.trace if row.requirement_id == requirement_id]
