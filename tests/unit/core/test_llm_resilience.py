"""Retry with back-off and response cache tests (NFR-06, FR-36, ADR-026, NFR-08).

NFR-06: when the OpenAI API fails the system retries with back-off and then
degrades to the mock or cached provider. ADR-026: live responses are cached so
a rerun costs nothing. A recording ``sleep`` makes the back-off testable without
waiting.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aitaf.core.errors import LlmError, LlmTransientError
from aitaf.core.llm import LlmGateway, LlmRequest, LlmResponse, MockProvider
from aitaf.core.llm.cache import CachingProvider
from aitaf.core.llm.retry import RetryingProvider
from aitaf.core.logging import set_run_id
from aitaf.core.metrics import Metrics
from aitaf.core.models import Run, RunStatus
from aitaf.core.storage import InMemoryRepository

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)


def request(prompt: str = "Summarise requirement R1", version: str = "ra-v1") -> LlmRequest:
    return LlmRequest(component="requirement_analyzer", prompt_version=version, prompt=prompt)


class Flaky:
    """Fails with the given errors in order, then answers."""

    name = "openai"
    model = "gpt-test"

    def __init__(self, *errors: Exception, mock: bool = False) -> None:
        self.errors = list(errors)
        self.calls = 0
        self.mock = mock

    def complete(self, req: LlmRequest) -> LlmResponse:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return LlmResponse(
            text=f"answer {self.calls}", model="gpt-test", tokens_in=4, tokens_out=2, mock=self.mock
        )


class Sleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


@pytest.fixture
def repo() -> Iterator[InMemoryRepository]:
    repository = InMemoryRepository()
    repository.create_run(
        Run(
            run_id="run-1",
            started_at=NOW,
            status=RunStatus.RUNNING,
            provider="openai",
            environment="test",
        )
    )
    set_run_id("run-1")
    yield repository
    set_run_id("")


# ------------------------------------------------------------------ retry


@pytest.mark.blackbox
def test_retry_succeeds_after_transient_failures_with_exponential_back_off() -> None:
    inner = Flaky(LlmTransientError("429"), LlmTransientError("429"))
    sleeper = Sleeper()
    response = RetryingProvider(inner, max_retries=3, base_delay_s=1.0, sleep=sleeper).complete(
        request()
    )
    assert response.text == "answer 3"
    assert inner.calls == 3
    assert sleeper.delays == [1.0, 2.0]


@pytest.mark.blackbox
def test_retry_gives_up_after_the_limit_and_raises_the_transient_error() -> None:
    inner = Flaky(*[LlmTransientError("503") for _ in range(10)])
    sleeper = Sleeper()
    with pytest.raises(LlmTransientError):
        RetryingProvider(inner, max_retries=2, sleep=sleeper).complete(request())
    assert inner.calls == 3  # first try plus two retries
    assert len(sleeper.delays) == 2


@pytest.mark.whitebox
def test_retry_does_not_repeat_permanent_errors() -> None:
    inner = Flaky(LlmError("bad key"))
    sleeper = Sleeper()
    with pytest.raises(LlmError):
        RetryingProvider(inner, max_retries=3, sleep=sleeper).complete(request())
    assert inner.calls == 1
    assert sleeper.delays == []


@pytest.mark.whitebox
def test_back_off_is_capped_at_the_maximum_delay() -> None:
    inner = Flaky(*[LlmTransientError("x") for _ in range(5)])
    sleeper = Sleeper()
    RetryingProvider(
        inner, max_retries=5, base_delay_s=2.0, max_delay_s=5.0, sleep=sleeper
    ).complete(request())
    assert sleeper.delays == [2.0, 4.0, 5.0, 5.0, 5.0]


@pytest.mark.whitebox
def test_zero_retries_means_a_single_attempt() -> None:
    inner = Flaky(LlmTransientError("x"))
    with pytest.raises(LlmTransientError):
        RetryingProvider(inner, max_retries=0, sleep=Sleeper()).complete(request())
    assert inner.calls == 1


@pytest.mark.whitebox
def test_retry_wrapper_keeps_the_inner_identity() -> None:
    wrapped = RetryingProvider(Flaky(), max_retries=1, sleep=Sleeper())
    assert wrapped.name == "openai"
    assert wrapped.model == "gpt-test"


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "kwargs", [{"max_retries": -1}, {"base_delay_s": -0.1}, {"max_delay_s": 0}]
)
def test_retry_rejects_invalid_settings(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        RetryingProvider(Flaky(), **kwargs)  # type: ignore[arg-type]


@pytest.mark.blackbox
def test_exhausted_retries_degrade_to_the_mock_provider_with_one_audit(
    repo: InMemoryRepository,
) -> None:
    """NFR-06 acceptance: API failure, retries, then mock fallback, one audit record."""
    inner = Flaky(*[LlmTransientError("503") for _ in range(10)])
    gateway = LlmGateway(
        RetryingProvider(inner, max_retries=2, sleep=Sleeper()),
        repo,
        call_cap=10,
        fallback=MockProvider(),
    )
    response = gateway.complete(request())
    assert response.mock is True
    (audit,) = repo.list_audits("run-1")
    assert audit.status == "fallback"
    assert inner.calls == 3


# ------------------------------------------------------------------ cache


@pytest.mark.blackbox
def test_identical_request_is_served_from_the_cache(tmp_path: Path) -> None:
    inner = Flaky()
    cached = CachingProvider(inner, tmp_path)
    first = cached.complete(request())
    second = cached.complete(request())
    assert inner.calls == 1
    assert second.text == first.text
    assert second.cached is True and first.cached is False
    assert second.mock is False


@pytest.mark.blackbox
def test_cache_survives_a_new_provider_instance(tmp_path: Path) -> None:
    CachingProvider(Flaky(), tmp_path).complete(request())
    inner = Flaky()
    hit = CachingProvider(inner, tmp_path).complete(request())
    assert inner.calls == 0
    assert hit.cached is True


@pytest.mark.whitebox
def test_a_different_prompt_or_prompt_version_is_a_miss(tmp_path: Path) -> None:
    inner = Flaky()
    cached = CachingProvider(inner, tmp_path)
    cached.complete(request("A"))
    cached.complete(request("B"))
    cached.complete(request("A", version="ra-v2"))
    assert inner.calls == 3


@pytest.mark.whitebox
def test_mock_responses_are_never_cached(tmp_path: Path) -> None:
    inner = Flaky(mock=True)
    cached = CachingProvider(inner, tmp_path)
    cached.complete(request())
    cached.complete(request())
    assert inner.calls == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.whitebox
def test_a_corrupt_cache_file_is_treated_as_a_miss_and_repaired(tmp_path: Path) -> None:
    inner = Flaky()
    cached = CachingProvider(inner, tmp_path)
    cached.complete(request())
    (entry,) = tmp_path.iterdir()
    entry.write_text("{not json", encoding="utf-8")
    again = cached.complete(request())
    assert again.cached is False
    assert inner.calls == 2
    assert json.loads(entry.read_text(encoding="utf-8"))["text"] == again.text


@pytest.mark.whitebox
def test_cache_files_hold_the_answer_but_not_the_prompt(tmp_path: Path) -> None:
    secret_prompt = "Login with password sk-live-DO-NOT-STORE"
    CachingProvider(Flaky(), tmp_path).complete(request(secret_prompt))
    (entry,) = tmp_path.iterdir()
    assert entry.suffix == ".json"
    assert len(entry.stem) == 64 and set(entry.stem) <= set("0123456789abcdef")
    assert "sk-live-DO-NOT-STORE" not in entry.read_text(encoding="utf-8")


@pytest.mark.whitebox
def test_errors_are_not_cached(tmp_path: Path) -> None:
    inner = Flaky(LlmTransientError("503"))
    cached = CachingProvider(inner, tmp_path)
    with pytest.raises(LlmTransientError):
        cached.complete(request())
    assert cached.complete(request()).cached is False
    assert inner.calls == 2


@pytest.mark.blackbox
def test_gateway_marks_cache_hits_and_charges_nothing(
    repo: InMemoryRepository, tmp_path: Path
) -> None:
    gateway = LlmGateway(
        CachingProvider(Flaky(), tmp_path),
        repo,
        call_cap=10,
        metrics=Metrics(repo),
        price_in_per_1k=1.0,
        price_out_per_1k=1.0,
    )
    gateway.complete(request())
    gateway.complete(request())
    audits = repo.list_audits("run-1")
    assert {audit.provider for audit in audits} == {"openai", "openai+cache"}
    assert all(audit.mock is False for audit in audits)
    costs = sorted(sample.cost_usd for sample in repo.list_metrics("run-1"))
    assert costs[0] == 0.0 and costs[1] > 0.0
