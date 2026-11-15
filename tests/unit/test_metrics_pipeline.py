"""Pipeline test: every implemented component emits latency and outcome metrics.

Requirements: NFR-35 (each component emits latency and outcome counters in a
pipeline test; token and cost logging), NFR-03 (healing latency is measurable),
FR-37 (audit records), NFR-17 (components talk through persistence).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.analyzer import (
    COMPONENT as ANALYZER,
)
from aitaf.analyzer import RequirementAnalyzer, load_requirements, mock_extraction_responder
from aitaf.core.errors import LlmTransientError
from aitaf.core.healing import FailureContext
from aitaf.core.llm import LlmGateway, LlmRequest, LlmResponse, MockProvider
from aitaf.core.logging import set_run_id
from aitaf.core.metrics import Metrics, run_cost
from aitaf.core.models import Locator, LocatorStrategy, ReviewStatus, Run, RunStatus
from aitaf.core.storage import InMemoryRepository
from aitaf.generator import COMPONENT as GENERATOR
from aitaf.generator import TestCaseGenerator, cases_for_scripting, mock_generation_responder
from aitaf.healing import SelfHealingEngine
from aitaf.scriptgen import COMPONENT as SCRIPTS
from aitaf.scriptgen import ScriptGenerator, mock_script_responder

DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=datetime(2026, 11, 14, tzinfo=UTC),
            status=RunStatus.RUNNING,
            provider="mock",
            environment="test",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


def run_pipeline(repo: InMemoryRepository, metrics: Metrics, out: Path) -> None:
    provider = MockProvider(
        responders={
            ANALYZER: mock_extraction_responder,
            GENERATOR: mock_generation_responder,
            SCRIPTS: mock_script_responder,
        }
    )
    gateway = LlmGateway(
        provider, repo, call_cap=200, metrics=metrics, price_in_per_1k=0.5, price_out_per_1k=1.5
    )
    analysed = RequirementAnalyzer(gateway, repo, metrics=metrics).analyze(
        load_requirements(DATA / "requirements" / "sample_requirements.md")
    )
    TestCaseGenerator(gateway, repo, metrics=metrics).generate(analysed.ready)
    for case in repo.list_test_cases("run-1")[:2]:
        repo.set_review_status("run-1", case.tc_id, ReviewStatus.APPROVED)
    ScriptGenerator(
        gateway,
        repo,
        framework="playwright",
        base_url="http://localhost:8000",
        allowed_hosts=frozenset({"localhost"}),
        output_dir=out,
        metrics=metrics,
    ).generate(cases_for_scripting(repo, "run-1", review_mode=True), repo.list_test_data("run-1"))
    locator = Locator(
        loc_id="login.login_button",
        page="login",
        name="login_button",
        primary=LocatorStrategy(kind="id", value="login-button"),
        fallbacks=[LocatorStrategy(kind="css", value="button[type=submit]")],
        model="mock-1",
        prompt_version="sg-v1",
    )
    SelfHealingEngine(repo, metrics=metrics).heal(
        FailureContext(
            step_ref="TC-1:step3",
            action="click",
            locator=locator,
            error_type="NoSuchElementException",
            error_message="",
            dom_html=(DATA / "dom" / "login_id_changed.html").read_text(encoding="utf-8"),
        )
    )


@pytest.mark.blackbox
def test_every_implemented_component_emits_latency_and_an_outcome(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    run_pipeline(repo, Metrics(repo), tmp_path / "out")
    samples = repo.list_metrics("run-1")
    seen = {(s.component, s.operation) for s in samples}
    for expected in (
        ("requirement_analyzer", "analyze"),
        ("test_case_generator", "generate"),
        ("script_generator", "generate"),
        ("self_healing", "heal"),
        ("llm_gateway", "requirement_analyzer"),
        ("llm_gateway", "test_case_generator"),
        ("llm_gateway", "script_generator"),
    ):
        assert expected in seen, expected
    assert all(s.outcome == "ok" and s.duration_ms >= 0 for s in samples)


@pytest.mark.blackbox
def test_gateway_metrics_match_the_audit_records_for_tokens_and_calls(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    run_pipeline(repo, Metrics(repo), tmp_path / "out")
    audits = repo.list_audits("run-1")
    gateway = [s for s in repo.list_metrics("run-1") if s.component == "llm_gateway"]
    assert len(gateway) == len(audits) > 0
    assert sum(s.tokens_in for s in gateway) == sum(a.tokens_in for a in audits)
    assert sum(s.tokens_out for s in gateway) == sum(a.tokens_out for a in audits)


@pytest.mark.blackbox
def test_cost_is_computed_from_tokens_and_configured_prices(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    run_pipeline(repo, Metrics(repo), tmp_path / "out")
    gateway = [s for s in repo.list_metrics("run-1") if s.component == "llm_gateway"]
    for s in gateway:
        assert s.cost_usd == pytest.approx(s.tokens_in / 1000 * 0.5 + s.tokens_out / 1000 * 1.5)
    assert run_cost(repo.list_metrics("run-1")) > 0


@pytest.mark.blackbox
def test_healing_outcome_is_recorded_as_detail(repo: InMemoryRepository, tmp_path: Path) -> None:
    run_pipeline(repo, Metrics(repo), tmp_path / "out")
    heal = next(s for s in repo.list_metrics("run-1") if s.component == "self_healing")
    assert heal.detail == "healed"


@pytest.mark.blackbox
def test_a_failed_llm_call_is_counted_as_an_error(repo: InMemoryRepository) -> None:
    class Failing:
        name = "failing"

        def complete(self, req: LlmRequest) -> LlmResponse:
            raise LlmTransientError("429")

    gateway = LlmGateway(Failing(), repo, call_cap=5, metrics=Metrics(repo))
    with pytest.raises(LlmTransientError):
        gateway.complete(
            LlmRequest(component="requirement_analyzer", prompt_version="v", prompt="p")
        )
    (sample,) = repo.list_metrics("run-1")
    assert sample.outcome == "error" and sample.component == "llm_gateway"


@pytest.mark.whitebox
def test_a_fallback_call_is_an_ok_sample_marked_fallback(repo: InMemoryRepository) -> None:
    class Failing:
        name = "failing"

        def complete(self, req: LlmRequest) -> LlmResponse:
            raise LlmTransientError("429")

    gateway = LlmGateway(
        Failing(), repo, call_cap=5, fallback=MockProvider(), metrics=Metrics(repo)
    )
    gateway.complete(LlmRequest(component="requirement_analyzer", prompt_version="v", prompt="p"))
    (sample,) = repo.list_metrics("run-1")
    assert sample.outcome == "ok" and sample.detail == "fallback"


@pytest.mark.whitebox
def test_components_work_without_a_metrics_object(repo: InMemoryRepository, tmp_path: Path) -> None:
    provider = MockProvider(responders={ANALYZER: mock_extraction_responder})
    analysed = RequirementAnalyzer(LlmGateway(provider, repo, call_cap=50), repo).analyze(
        load_requirements(DATA / "requirements" / "sample_plain.txt")
    )
    assert analysed.ready and repo.list_metrics("run-1") == []
