"""OpenAI provider tests with a fake client (FR-36, NFR-06, NFR-09, NFR-25).

No network access and no key are needed: the provider takes an injected client,
so every OpenAI outcome (success, rate limit, timeout, server error, bad key) is
scripted. Errors must be translated into the framework hierarchy and must never
carry the API key.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx2
import openai
import pytest

from aitaf.core.errors import LlmError, LlmTransientError
from aitaf.core.llm import LlmRequest
from aitaf.core.llm.openai_provider import OpenAIProvider

KEY = "sk-test-DO-NOT-LEAK-1234567890"
REQUEST = httpx2.Request("POST", "https://api.example.invalid/v1/chat/completions")


class FakeCompletions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def fake_client(*outcomes: Any) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(list(outcomes))))


def completion(text: str | None = "hello", model: str = "gpt-test-1", pin: int = 5, pout: int = 3):
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=pin, completion_tokens=pout),
    )


def status_error(cls: type[openai.APIStatusError], code: int) -> openai.APIStatusError:
    return cls("upstream said no", response=httpx2.Response(code, request=REQUEST), body=None)


def request(prompt: str = "Summarise requirement R1") -> LlmRequest:
    return LlmRequest(component="requirement_analyzer", prompt_version="ra-v1", prompt=prompt)


def provider(client: Any, **kwargs: Any) -> OpenAIProvider:
    return OpenAIProvider(api_key=KEY, model="gpt-test", client=client, **kwargs)


@pytest.mark.blackbox
def test_successful_call_returns_a_live_response_with_usage() -> None:
    response = provider(fake_client(completion("answer", "gpt-test-1", 11, 7))).complete(request())
    assert response.text == "answer"
    assert response.model == "gpt-test-1"
    assert (response.tokens_in, response.tokens_out) == (11, 7)
    assert response.mock is False
    assert response.cached is False


@pytest.mark.blackbox
def test_provider_identifies_itself_for_the_audit() -> None:
    assert provider(fake_client()).name == "openai"


@pytest.mark.whitebox
def test_request_sends_one_user_message_with_model_timeout_and_zero_temperature() -> None:
    client = fake_client(completion())
    provider(client, timeout_s=12.5).complete(request("the prompt"))
    (call,) = client.chat.completions.calls
    assert call["model"] == "gpt-test"
    assert call["messages"] == [{"role": "user", "content": "the prompt"}]
    assert call["temperature"] == 0.0
    assert call["timeout"] == 12.5


@pytest.mark.whitebox
def test_temperature_can_be_left_to_the_model_default() -> None:
    client = fake_client(completion())
    provider(client, temperature=None).complete(request())
    assert "temperature" not in client.chat.completions.calls[0]


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "error",
    [
        status_error(openai.RateLimitError, 429),
        status_error(openai.InternalServerError, 500),
        openai.APIConnectionError(request=REQUEST),
        openai.APITimeoutError(request=REQUEST),
    ],
    ids=["rate-limit", "server-error", "connection", "timeout"],
)
def test_transient_openai_failures_become_transient_errors(error: Exception) -> None:
    with pytest.raises(LlmTransientError):
        provider(fake_client(error)).complete(request())


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "error",
    [
        status_error(openai.AuthenticationError, 401),
        status_error(openai.APIStatusError, 400),
    ],
    ids=["bad-key", "bad-request"],
)
def test_permanent_openai_failures_are_not_transient(error: Exception) -> None:
    with pytest.raises(LlmError) as info:
        provider(fake_client(error)).complete(request())
    assert not isinstance(info.value, LlmTransientError)


@pytest.mark.whitebox
@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_model_output_is_an_error(text: str | None) -> None:
    with pytest.raises(LlmError):
        provider(fake_client(completion(text))).complete(request())


@pytest.mark.whitebox
def test_missing_usage_is_counted_as_zero_tokens() -> None:
    result = completion("x")
    result.usage = None
    response = provider(fake_client(result)).complete(request())
    assert (response.tokens_in, response.tokens_out) == (0, 0)


@pytest.mark.blackbox
def test_api_key_never_appears_in_repr_or_error_messages() -> None:
    llm = provider(fake_client(status_error(openai.AuthenticationError, 401)))
    assert KEY not in repr(llm) and KEY not in str(llm.__dict__.get("model", ""))
    with pytest.raises(LlmError) as info:
        llm.complete(request())
    assert KEY not in str(info.value)
    assert KEY not in repr(info.value)


@pytest.mark.whitebox
def test_a_blank_key_or_model_is_rejected_at_construction() -> None:
    with pytest.raises(LlmError):
        OpenAIProvider(api_key="  ", model="gpt-test", client=fake_client())
    with pytest.raises(LlmError):
        OpenAIProvider(api_key=KEY, model="", client=fake_client())
