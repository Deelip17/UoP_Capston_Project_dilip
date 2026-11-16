"""CLI skeleton and configuration-file tests.

Requirements: FR-35 (command-line interface driven by a configuration file,
invalid configuration rejected with a clear message), NFR-09 (no API key in a
configuration file).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aitaf.cli import STAGES, main
from aitaf.core.config import Settings
from aitaf.core.errors import ConfigError


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LLM_PROVIDER",
        "LLM_CALL_CAP",
        "LOG_LEVEL",
        "OPENAI_API_KEY",
        "LLM_MODEL",
        "LLM_MAX_RETRIES",
        "LLM_TIMEOUT_S",
        "LLM_CACHE_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


def write_config(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "aitaf.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.blackbox
def test_help_lists_run_and_every_stage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "run" in out
    for stage in STAGES:
        assert stage in out


@pytest.mark.blackbox
def test_missing_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


@pytest.mark.blackbox
def test_invalid_config_is_rejected_with_clear_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path, {"llm_provider": "banana"})
    assert main(["run", "--input", "r.md", "--config", str(path)]) == 2
    assert "LLM_PROVIDER" in capsys.readouterr().err


@pytest.mark.blackbox
def test_missing_config_file_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["run", "--input", "r.md", "--config", str(tmp_path / "nope.json")]) == 2
    assert "nope.json" in capsys.readouterr().err


@pytest.mark.blackbox
def test_run_without_a_system_under_test_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path, {"llm_provider": "mock", "llm_call_cap": 5})
    assert main(["run", "--input", "r.md", "--config", str(path)]) == 2
    assert "--demo-shop or --base-url" in capsys.readouterr().err


@pytest.mark.whitebox
def test_config_file_values_are_loaded() -> None:
    settings = Settings.from_file_data({"llm_provider": "mock", "llm_call_cap": 7}, env={})
    assert settings.llm_call_cap == 7


@pytest.mark.whitebox
def test_environment_overrides_config_file() -> None:
    settings = Settings.from_file_data({"llm_call_cap": 7}, env={"LLM_CALL_CAP": "9"})
    assert settings.llm_call_cap == 9


@pytest.mark.whitebox
def test_api_key_in_config_file_is_rejected() -> None:
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        Settings.from_file_data({"openai_api_key": "sk-nope"}, env={})


@pytest.mark.whitebox
def test_unknown_config_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="unknown"):
        Settings.from_file_data({"surprise": 1}, env={})


@pytest.mark.whitebox
def test_config_file_that_is_not_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        Settings.from_file(path, env={})


@pytest.mark.whitebox
def test_config_file_must_hold_an_object(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ConfigError, match="JSON object"):
        Settings.from_file(path, env={})


@pytest.mark.whitebox
def test_unreadable_config_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read"):
        Settings.from_file(tmp_path, env={})


DATA = Path(__file__).resolve().parents[2] / "data" / "requirements"


@pytest.mark.blackbox
def test_analyze_command_runs_on_sample_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    code = main(["analyze", "--input", str(DATA / "sample_requirements.md"), "--db", str(db)])
    out = capsys.readouterr().out
    assert code == 0
    assert "4 ready, 3 flagged, 0 rejected" in out
    assert "mock-generated" in out
    assert db.exists()


@pytest.mark.blackbox
def test_analyze_rejects_unsupported_input_with_clear_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "reqs.docx"
    bad.write_bytes(b"x")
    assert main(["analyze", "--input", str(bad), "--db", str(tmp_path / "a.db")]) == 1
    assert ".md" in capsys.readouterr().err


@pytest.mark.blackbox
def test_analyze_requires_input(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["analyze"])
    assert exit_info.value.code == 2


@pytest.mark.blackbox
def test_analyze_with_a_failing_live_provider_completes_through_the_mock_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-06 end to end: the live API fails, the pipeline still finishes offline."""
    from aitaf.core.errors import LlmTransientError
    from aitaf.core.llm import LlmRequest, LlmResponse, MockProvider

    class Down:
        name = "openai"

        def complete(self, req: LlmRequest) -> LlmResponse:
            raise LlmTransientError("simulated outage")

    def fake_build(settings: Settings, responders=None, openai_client=None):  # type: ignore[no-untyped-def]
        return Down(), MockProvider(responders=responders)

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder-value")
    monkeypatch.setattr("aitaf.cli.build_providers", fake_build)
    db = tmp_path / "a.db"
    assert main(["analyze", "--input", str(DATA / "sample_plain.txt"), "--db", str(db)]) == 0
    from aitaf.core.storage import SqliteRepository

    repo = SqliteRepository(db)
    try:
        run_id = repo.latest_run_with_requirements()
        assert run_id is not None
        statuses = {audit.status for audit in repo.list_audits(run_id)}
    finally:
        repo.close()
    assert statuses == {"fallback"}


@pytest.mark.blackbox
def test_live_output_is_labelled_as_ai_generated_not_mock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-30: output from the live provider must not be labelled mock."""
    from aitaf.core.llm import MockProvider

    def fake_build(settings: Settings, responders=None, openai_client=None):  # type: ignore[no-untyped-def]
        return MockProvider(responders=responders), None

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder-value")
    monkeypatch.setenv("LLM_MODEL", "gpt-test")
    monkeypatch.setattr("aitaf.cli.build_providers", fake_build)
    code = main(
        ["analyze", "--input", str(DATA / "sample_plain.txt"), "--db", str(tmp_path / "a.db")]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "mock-generated" not in out
    assert "AI-generated output from gpt-test" in out


@pytest.mark.whitebox
def test_openai_provider_without_a_key_is_a_configuration_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    code = main(
        ["analyze", "--input", str(DATA / "sample_plain.txt"), "--db", str(tmp_path / "a.db")]
    )
    assert code == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def analyze_sample(db: Path) -> None:
    assert main(["analyze", "--input", str(DATA / "sample_requirements.md"), "--db", str(db)]) == 0


@pytest.mark.blackbox
def test_generate_command_builds_cases_for_ready_requirements_and_exports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    analyze_sample(db)
    capsys.readouterr()
    out_dir = tmp_path / "export"
    code = main(["generate", "--db", str(db), "--export-dir", str(out_dir)])
    out = capsys.readouterr().out
    assert code == 0
    assert "12 test cases" in out
    assert "3 skipped" in out
    assert "0 duplicates removed" in out
    assert "mock-generated" in out
    assert sorted(p.suffix for p in out_dir.iterdir()) == [".csv", ".json", ".md"]


@pytest.mark.blackbox
def test_generate_without_analysed_requirements_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["generate", "--db", str(tmp_path / "empty.db")]) == 1
    assert "analyze" in capsys.readouterr().err


@pytest.mark.blackbox
def test_review_command_changes_status_and_scripting_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    analyze_sample(db)
    assert main(["generate", "--db", str(db)]) == 0
    capsys.readouterr()
    assert main(["review", "--db", str(db), "--list"]) == 0
    first_id = capsys.readouterr().out.split()[0]
    assert main(["review", "--db", str(db), "--approve", first_id]) == 0
    capsys.readouterr()
    assert main(["review", "--db", str(db), "--list", "--status", "Approved"]) == 0
    assert capsys.readouterr().out.split()[0] == first_id


@pytest.mark.blackbox
def test_review_of_unknown_case_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    analyze_sample(db)
    assert main(["generate", "--db", str(db)]) == 0
    capsys.readouterr()
    assert main(["review", "--db", str(db), "--approve", "TC-NOPE"]) == 1
    assert "TC-NOPE" in capsys.readouterr().err


def prepare_cases(db: Path, capsys: pytest.CaptureFixture[str]) -> str:
    analyze_sample(db)
    assert main(["generate", "--db", str(db)]) == 0
    capsys.readouterr()
    assert main(["review", "--db", str(db), "--list"]) == 0
    first_id = capsys.readouterr().out.split()[0]
    return first_id


@pytest.mark.blackbox
def test_script_command_scripts_only_approved_cases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    first_id = prepare_cases(db, capsys)
    assert main(["review", "--db", str(db), "--approve", first_id]) == 0
    capsys.readouterr()
    out_dir = tmp_path / "gen"
    assert main(["script", "--db", str(db), "--out-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert "1 scripts written (playwright)" in out
    assert "0 rejected" in out
    assert len(list((out_dir / "tests").glob("test_*.py"))) == 1
    assert (out_dir / "manifest.json").exists()


@pytest.mark.blackbox
def test_script_command_with_pages_uses_only_elements_found_on_the_pages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    first_id = prepare_cases(db, capsys)
    assert main(["review", "--db", str(db), "--approve", first_id]) == 0
    capsys.readouterr()
    out_dir = tmp_path / "gen"
    pages = Path(__file__).resolve().parents[2] / "data" / "dom" / "shop"
    args = ["script", "--db", str(db), "--out-dir", str(out_dir), "--pages", str(pages)]
    assert main(args) == 0
    assert "1 scripts written" in capsys.readouterr().out
    repo_file = (out_dir / "locators" / "shop_locators.py").read_text(encoding="utf-8")
    assert "('id', '" in repo_file  # built from the pages
    assert main([*args[:-1], str(tmp_path / "missing")]) == 1


@pytest.mark.blackbox
def test_script_command_with_nothing_approved_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    prepare_cases(db, capsys)
    out_dir = tmp_path / "gen"
    assert main(["script", "--db", str(db), "--out-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert "0 scripts written" in out and "aitaf review" in out
    assert not out_dir.exists()


@pytest.mark.blackbox
def test_script_command_without_review_mode_scripts_pending_cases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    prepare_cases(db, capsys)
    out_dir = tmp_path / "gen"
    code = main(
        [
            "script",
            "--db",
            str(db),
            "--out-dir",
            str(out_dir),
            "--no-review",
            "--framework",
            "selenium",
        ]
    )
    assert code == 0
    assert "12 scripts written (selenium)" in capsys.readouterr().out
    assert "selenium" in (out_dir / "conftest.py").read_text(encoding="utf-8")


@pytest.mark.blackbox
def test_script_command_refuses_a_host_outside_the_allow_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    prepare_cases(db, capsys)
    code = main(["script", "--db", str(db), "--base-url", "http://client-system.example"])
    assert code == 1
    assert "allow-list" in capsys.readouterr().err


@pytest.mark.blackbox
def test_script_command_accepts_an_explicitly_allowed_host(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    prepare_cases(db, capsys)
    out_dir = tmp_path / "gen"
    code = main(
        [
            "script",
            "--db",
            str(db),
            "--out-dir",
            str(out_dir),
            "--no-review",
            "--base-url",
            "http://demo.example",
            "--allow-host",
            "demo.example",
        ]
    )
    assert code == 0
    assert "http://demo.example" in (out_dir / "conftest.py").read_text(encoding="utf-8")


DOM = Path(__file__).resolve().parents[2] / "data" / "dom"


def heal_args(after: str, *extra: str, db: Path) -> list[str]:
    return [
        "heal",
        "--db",
        str(db),
        "--before",
        str(DOM / "login_before.html"),
        "--after",
        str(DOM / after),
        "--primary",
        "id=login-button",
        "--fallback",
        "css=button[type=submit]",
        *extra,
    ]


@pytest.mark.blackbox
def test_heal_command_repairs_via_a_stored_fallback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(heal_args("login_id_changed.html", db=tmp_path / "h.db")) == 0
    out = capsys.readouterr().out
    assert "locator failure" in out
    assert "HEALED" in out and "fallback" in out and "awaiting human approval" in out


@pytest.mark.blackbox
def test_heal_command_repairs_via_dom_similarity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(heal_args("login_all_changed.html", db=tmp_path / "h.db")) == 0
    out = capsys.readouterr().out
    assert "similarity" in out and "HEALED" in out and "id=go-4271" in out


@pytest.mark.blackbox
def test_heal_command_reaches_the_llm_step_only_when_enabled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(heal_args("login_renamed.html", db=tmp_path / "off.db")) == 1
    assert "NOT HEALED" in capsys.readouterr().out
    assert main(heal_args("login_renamed.html", "--llm", db=tmp_path / "on.db")) == 0
    out = capsys.readouterr().out
    assert "HEALED" in out and "llm" in out and "mock-generated" in out


@pytest.mark.blackbox
def test_heal_command_rejects_a_present_but_wrong_element(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(heal_args("login_wrong_element.html", db=tmp_path / "h.db")) == 1
    out = capsys.readouterr().out
    assert "rejected" in out and "NOT HEALED" in out and "step still fails" in out


@pytest.mark.blackbox
def test_heal_command_leaves_application_defects_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        heal_args(
            "login_id_changed.html",
            "--error",
            "AssertionError",
            "--message",
            "assert 1 == 2",
            db=tmp_path / "h.db",
        )
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "application defect" in out and "not healable" in out.lower()


@pytest.mark.blackbox
def test_heal_command_rejects_a_malformed_strategy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = heal_args("login_id_changed.html", db=tmp_path / "h.db")
    args[args.index("id=login-button")] = "nonsense"
    assert main(args) == 2
    assert "kind=value" in capsys.readouterr().err


@pytest.mark.blackbox
def test_heal_command_needs_the_primary_to_resolve_in_the_before_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = heal_args("login_id_changed.html", db=tmp_path / "h.db")
    args[args.index("id=login-button")] = "id=not-on-the-page"
    assert main(args) == 1
    assert "--before" in capsys.readouterr().err


@pytest.mark.blackbox
def test_metrics_command_reports_latency_tokens_and_cost_per_component(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    analyze_sample(db)
    assert main(["generate", "--db", str(db)]) == 0
    capsys.readouterr()
    assert main(["metrics", "--db", str(db)]) == 0
    out = capsys.readouterr().out
    for name in ("requirement_analyzer", "test_case_generator", "llm_gateway"):
        assert name in out
    assert "median_ms" in out and "tokens_in" in out and "cost_usd" in out
    assert "total cost" in out


@pytest.mark.blackbox
def test_metrics_command_prices_tokens_from_the_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "aitaf.db"
    monkeypatch.setenv("LLM_PRICE_IN_PER_1K", "1.0")
    monkeypatch.setenv("LLM_PRICE_OUT_PER_1K", "2.0")
    analyze_sample(db)
    capsys.readouterr()
    assert main(["metrics", "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "total cost: $0.0000" not in out and "total cost: $" in out


@pytest.mark.blackbox
def test_metrics_command_without_data_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["metrics", "--db", str(tmp_path / "empty.db")]) == 1
    assert "no metrics" in capsys.readouterr().err


@pytest.mark.blackbox
def test_metrics_command_for_an_unknown_run_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "aitaf.db"
    analyze_sample(db)
    capsys.readouterr()
    assert main(["metrics", "--db", str(db), "--run", "nope"]) == 1
    assert "no metrics" in capsys.readouterr().err


# ---------------------------------------------- label after a provider outage (D-009)


class _FailingFirst:
    """Primary provider that fails ``failures`` times, then answers like the mock."""

    name = "openai"

    def __init__(self, failures: int, responders=None) -> None:  # type: ignore[no-untyped-def]
        from aitaf.core.llm import MockProvider

        self._failures = failures
        self._inner = MockProvider(responders=responders)

    def complete(self, req):  # type: ignore[no-untyped-def]
        from aitaf.core.errors import LlmTransientError

        if self._failures > 0:
            self._failures -= 1
            raise LlmTransientError("simulated outage")
        return self._inner.complete(req)


def _analyze_live_with(failures: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aitaf.core.llm import MockProvider

    def fake_build(settings: Settings, responders=None, openai_client=None):  # type: ignore[no-untyped-def]
        return _FailingFirst(failures, responders), MockProvider(responders=responders)

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder-value")
    monkeypatch.setenv("LLM_MODEL", "gpt-test")
    monkeypatch.setattr("aitaf.cli.build_providers", fake_build)
    assert (
        main(["analyze", "--input", str(DATA / "sample_plain.txt"), "--db", str(tmp_path / "a.db")])
        == 0
    )


@pytest.mark.blackbox
def test_output_is_not_labelled_live_when_every_call_fell_back_to_the_mock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-009 (NFR-30): a run whose every model call failed must say the mock answered."""
    _analyze_live_with(1000, tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "AI-generated output from gpt-test" not in out
    assert "live provider failed" in out and "mock" in out


@pytest.mark.blackbox
def test_output_says_how_many_calls_fell_back_when_only_some_did(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _analyze_live_with(1, tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "AI-generated output from gpt-test" in out
    assert "1 of 2 call(s) fell back to the mock" in out
