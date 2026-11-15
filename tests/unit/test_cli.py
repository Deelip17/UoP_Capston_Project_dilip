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
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "LOG_LEVEL", "OPENAI_API_KEY"):
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
    assert main(["run", "--config", str(path)]) == 2
    assert "LLM_PROVIDER" in capsys.readouterr().err


@pytest.mark.blackbox
def test_missing_config_file_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["run", "--config", str(tmp_path / "nope.json")]) == 2
    assert "nope.json" in capsys.readouterr().err


@pytest.mark.blackbox
def test_valid_config_reaches_unimplemented_stage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(tmp_path, {"llm_provider": "mock", "llm_call_cap": 5})
    assert main(["generate", "--config", str(path)]) == 3
    assert "not implemented" in capsys.readouterr().err


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


@pytest.mark.whitebox
def test_analyze_refuses_openai_provider_until_implemented(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-placeholder-value")
    code = main(
        ["analyze", "--input", str(DATA / "sample_plain.txt"), "--db", str(tmp_path / "a.db")]
    )
    assert code == 2
    assert "mock" in capsys.readouterr().err
