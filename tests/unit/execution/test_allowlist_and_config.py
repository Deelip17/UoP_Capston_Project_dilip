"""Base-URL allow-list and run configuration (FR-21, FR-17, FR-20, NFR-11, ADR-005).

FR-21 acceptance: a run targeting a non-listed URL aborts before any browser
action and logs the reason. The check must resist look-alike hosts, embedded
credentials and unusual schemes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from aitaf.core.errors import PolicyError
from aitaf.execution import RunConfig, check_base_url

HOSTS = ["127.0.0.1", "localhost"]


@pytest.mark.blackbox
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://127.0.0.1:8765", "http://127.0.0.1:8765"),
        ("HTTP://LocalHost:8080/", "http://localhost:8080"),
        ("https://localhost", "https://localhost"),
        ("http://127.0.0.1/shop/", "http://127.0.0.1"),
    ],
)
def test_listed_hosts_are_accepted_and_normalised(url: str, expected: str) -> None:
    assert check_base_url(url, HOSTS) == expected


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "http://127.0.0.1.evil.test",
        "http://evil.test#@127.0.0.1",
        "http://evil.test/127.0.0.1",
        "http://localhost.evil.test:8000",
    ],
)
def test_other_hosts_are_refused_with_the_reason(url: str) -> None:
    with pytest.raises(PolicyError, match="allow-list"):
        check_base_url(url, HOSTS)


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://localhost", "javascript:alert(1)", "localhost:8000", ""]
)
def test_only_http_and_https_with_a_host_are_accepted(url: str) -> None:
    with pytest.raises(PolicyError):
        check_base_url(url, HOSTS)


@pytest.mark.blackbox
def test_credentials_in_the_url_are_refused_and_not_echoed() -> None:
    with pytest.raises(PolicyError) as info:
        check_base_url("http://admin:s3cr3t-value@127.0.0.1", HOSTS)
    assert "s3cr3t-value" not in str(info.value)
    assert "admin" not in str(info.value)


@pytest.mark.whitebox
@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:99999", "http://127.0.0.1:abc", "http://127.0.0.1 \n"]
)
def test_bad_ports_and_whitespace_are_refused(url: str) -> None:
    with pytest.raises(PolicyError):
        check_base_url(url, HOSTS)


@pytest.mark.whitebox
def test_an_empty_allow_list_refuses_everything() -> None:
    with pytest.raises(PolicyError, match="allow-list"):
        check_base_url("http://127.0.0.1", [])


@pytest.mark.whitebox
def test_the_allow_list_is_compared_without_case_or_blank_entries() -> None:
    assert check_base_url("http://example.test", ["  Example.TEST ", ""]) == "http://example.test"


# ------------------------------------------------------------------ config


def config(**extra: object) -> RunConfig:
    base: dict[str, object] = {
        "scripts_dir": Path("scripts"),
        "base_url": "http://127.0.0.1:8765",
        "allowed_hosts": ["127.0.0.1"],
        "evidence_dir": Path("evidence"),
    }
    return RunConfig(**{**base, **extra})  # type: ignore[arg-type]


@pytest.mark.blackbox
def test_defaults_match_the_requirements() -> None:
    cfg = config()
    assert cfg.driver == "playwright" and cfg.headless is True
    assert cfg.retries == 0 and cfg.workers == 1 and cfg.checkpoints is False
    assert cfg.timeout_ms == 10_000 and cfg.run_timeout_s == 600


@pytest.mark.blackbox
@pytest.mark.parametrize(
    "extra",
    [
        {"driver": "cypress"},
        {"retries": -1},
        {"retries": 6},
        {"workers": 0},
        {"workers": 9},
        {"timeout_ms": 50},
        {"timeout_ms": 400_000},
        {"run_timeout_s": 0},
        {"allowed_hosts": []},
        {"allowed_hosts": ["  "]},
        {"unknown_option": 1},
    ],
)
def test_out_of_range_settings_are_rejected(extra: dict[str, object]) -> None:
    with pytest.raises(PydanticValidationError):
        config(**extra)


@pytest.mark.whitebox
def test_hosts_are_lowercased_and_trimmed_and_the_config_is_frozen() -> None:
    cfg = config(allowed_hosts=[" LocalHost ", "127.0.0.1"])
    assert cfg.allowed_hosts == ("localhost", "127.0.0.1")
    with pytest.raises(PydanticValidationError):
        cfg.retries = 3  # type: ignore[misc]


@pytest.mark.blackbox
def test_relative_folders_are_made_absolute_so_pytest_can_find_its_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = RunConfig(
        scripts_dir=Path("scripts"),
        base_url="http://127.0.0.1:1",
        allowed_hosts=("127.0.0.1",),
        evidence_dir=Path("reports/runs/r1"),
    )
    assert config.scripts_dir == (tmp_path / "scripts").resolve()
    assert config.evidence_dir == (tmp_path / "reports" / "runs" / "r1").resolve()
