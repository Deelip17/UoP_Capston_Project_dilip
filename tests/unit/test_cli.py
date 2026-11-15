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
    assert main(["analyze", "--config", str(path)]) == 3
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
