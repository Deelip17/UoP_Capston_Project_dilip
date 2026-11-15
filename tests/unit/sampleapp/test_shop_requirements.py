"""The 20-requirement set for the sample shop (Unit 6 evaluation, FR-01 to FR-05, FR-38).

The set was fixed before any measurement: 18 clear requirements and 2 deliberately
vague ones ("easy", "fast") that the analyzer must flag. It also acts as a regression
test for the injection screen, which once rejected a legitimate requirement that
mentioned the word "password" (see PROGRESS_LOG.md).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aitaf.cli import main

REQUIREMENTS = (
    Path(__file__).resolve().parents[3] / "data" / "requirements" / "shop_requirements.md"
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LLM_PROVIDER", "LLM_CALL_CAP", "OPENAI_API_KEY", "LLM_MODEL", "LLM_CACHE_DIR"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.blackbox
def test_the_set_has_exactly_twenty_requirements_and_no_stray_text() -> None:
    lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    bullets = [line for line in lines if line.startswith("- ")]
    others = [line for line in lines if line and not line.startswith(("- ", "#"))]
    assert len(bullets) == 20
    assert others == []


@pytest.mark.blackbox
def test_analyzer_accepts_eighteen_and_flags_the_two_vague_requirements(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["analyze", "--input", str(REQUIREMENTS), "--db", str(tmp_path / "shop.db")]) == 0
    out = capsys.readouterr().out
    assert "summary: 18 ready, 2 flagged, 0 rejected" in out
    flagged = re.findall(r"vague wording: '(\w+)'", out)
    assert sorted(flagged) == ["easy", "fast"]


@pytest.mark.whitebox
def test_requirements_describe_only_behaviour_the_shop_has() -> None:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    for word in (
        "Backpack",
        "Desk Lamp",
        "Notebook",
        "Invalid email or password",
        "Your cart is empty",
    ):
        assert word in text
