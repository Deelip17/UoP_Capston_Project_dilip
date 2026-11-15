"""LLM provider contract and LLM Gateway tests.

Requirements: FR-36 (mock/fallback provider), FR-37 (one audit record per call,
no secrets or raw prompts), NFR-25 (providers behind an interface), ADR-026
(call cap), NFR-14 (audit of LLM calls).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from aitaf.core.errors import LlmTransientError, PolicyError
from aitaf.core.llm import LlmGateway, LlmProvider, LlmRequest, LlmResponse, MockProvider
from aitaf.core.logging import set_run_id
from aitaf.core.models import Run, RunStatus
from aitaf.core.storage import InMemoryRepository

NOW = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
SECRET_PROMPT = "Login must accept user alice with password sk-live-DO-NOT-STORE"


def request(prompt: str = "Summarise requirement R1", component: str = "requirement_analyzer"):
    return LlmRequest(component=component, prompt_version="ra-v1", prompt=prompt)


class ScriptedProvider:
    """Test double standing in for a second provider implementation (NFR-25)."""

    name = "scripted"

    def complete(self, req: LlmRequest) -> LlmResponse:
        return LlmResponse(
            text="scripted", model="scripted-1", tokens_in=1, tokens_out=1, mock=False
        )


class FailingProvider:
    name = "failing"

    def complete(self, req: LlmRequest) -> LlmResponse:
        raise LlmTransientError("simulated 429")


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


@pytest.fixture(params=["mock", "scripted"])
def provider(request: pytest.FixtureRequest) -> LlmProvider:
    return MockProvider() if request.param == "mock" else ScriptedProvider()


@pytest.mark.blackbox
def test_provider_contract_returns_well_formed_response(provider: LlmProvider) -> None:
    response = provider.complete(request())
    assert response.text
    assert response.model
    assert response.tokens_in >= 0 and response.tokens_out >= 0


@pytest.mark.blackbox
def test_mock_provider_is_deterministic_and_labelled_mock() -> None:
    first = MockProvider().complete(request())
    second = MockProvider().complete(request())
    assert first == second
    assert first.mock is True


@pytest.mark.blackbox
def test_mock_provider_differs_for_different_prompts() -> None:
    assert MockProvider().complete(request("a")).text != MockProvider().complete(request("b")).text


@pytest.mark.whitebox
def test_mock_provider_returns_recorded_response_for_known_hash() -> None:
    digest = hashlib.sha256(b"known prompt").hexdigest()
    mock = MockProvider(recorded={digest: '{"recorded": true}'})
    assert mock.complete(request("known prompt")).text == '{"recorded": true}'


@pytest.mark.blackbox
def test_gateway_writes_exactly_one_audit_per_call(repo: InMemoryRepository) -> None:
    gateway = LlmGateway(MockProvider(), repo, call_cap=10)
    gateway.complete(request("one"))
    gateway.complete(request("two"))
    audits = repo.list_audits("run-1")
    assert len(audits) == 2
    assert {a.status for a in audits} == {"ok"}
    assert all(a.mock for a in audits)


@pytest.mark.blackbox
def test_audit_hashes_input_and_never_stores_prompt_or_secret(repo: InMemoryRepository) -> None:
    gateway = LlmGateway(MockProvider(), repo, call_cap=10)
    gateway.complete(request(SECRET_PROMPT))
    (audit,) = repo.list_audits("run-1")
    assert audit.input_hash == hashlib.sha256(SECRET_PROMPT.encode()).hexdigest()
    dump = audit.model_dump_json()
    assert "sk-live" not in dump
    assert "password" not in dump


@pytest.mark.blackbox
def test_gateway_enforces_call_cap(repo: InMemoryRepository) -> None:
    gateway = LlmGateway(MockProvider(), repo, call_cap=2)
    gateway.complete(request("1"))
    gateway.complete(request("2"))
    with pytest.raises(PolicyError):
        gateway.complete(request("3"))
    assert len(repo.list_audits("run-1")) == 2


@pytest.mark.whitebox
def test_zero_cap_blocks_every_call(repo: InMemoryRepository) -> None:
    with pytest.raises(PolicyError):
        LlmGateway(MockProvider(), repo, call_cap=0).complete(request())
    assert repo.list_audits("run-1") == []


@pytest.mark.blackbox
def test_transient_failure_falls_back_to_mock_and_is_marked(repo: InMemoryRepository) -> None:
    gateway = LlmGateway(FailingProvider(), repo, call_cap=10, fallback=MockProvider())
    response = gateway.complete(request())
    assert response.mock is True
    (audit,) = repo.list_audits("run-1")
    assert audit.status == "fallback"
    assert audit.mock is True


@pytest.mark.whitebox
def test_failure_without_fallback_is_audited_then_raised(repo: InMemoryRepository) -> None:
    gateway = LlmGateway(FailingProvider(), repo, call_cap=10)
    with pytest.raises(LlmTransientError):
        gateway.complete(request())
    (audit,) = repo.list_audits("run-1")
    assert audit.status == "error"
    assert audit.tokens_in == 0 and audit.tokens_out == 0


@pytest.mark.whitebox
def test_gateway_requires_a_run_id(repo: InMemoryRepository) -> None:
    set_run_id("")
    with pytest.raises(PolicyError):
        LlmGateway(MockProvider(), repo, call_cap=10).complete(request())


@pytest.mark.whitebox
def test_live_provider_response_is_not_marked_mock(repo: InMemoryRepository) -> None:
    LlmGateway(ScriptedProvider(), repo, call_cap=10).complete(request())
    (audit,) = repo.list_audits("run-1")
    assert audit.mock is False
    assert audit.provider == "scripted"
