"""Data masking tests: secrets and personal data never survive masking.

Requirements: FR-30 (redact secrets and personal data before any LLM call),
NFR-15 (redaction precedes every LLM call), NFR-09.
"""

from __future__ import annotations

import pytest

from aitaf.core.errors import MaskingError
from aitaf.core.masking import is_synthetic_safe, mask

SEEDED = {
    "email": "jane.doe@example.com",
    "openai key": "sk-" + "abcdEFGH12345678xyz",
    "aws key": "AKIA" + "ABCDEFGHIJKLMNOP",
    "github token": "ghp_" + "abcdefghijklmnopqrstuvwxyz0123",
    "bearer": "Bearer eyJhbGciOi.payload.signature",
    "password": "password=Hunter2Hunter2",
    "card": "4111 1111 1111 1111",
    "ssn": "123-45-6789",
    "phone": "+1 555-123-4567",
}


@pytest.mark.blackbox
@pytest.mark.parametrize("label", sorted(SEEDED))
def test_seeded_sensitive_value_is_removed(label: str) -> None:
    value = SEEDED[label]
    result = mask(f"Customer detail: {value} was supplied.")
    secret_part = value.split("=")[-1] if label == "password" else value
    assert secret_part not in result.text
    assert result.total >= 1


@pytest.mark.blackbox
def test_all_seeded_values_in_one_text_are_removed() -> None:
    text = " | ".join(SEEDED.values())
    masked = mask(text).text
    for label, value in SEEDED.items():
        part = value.split("=")[-1] if label == "password" else value
        assert part not in masked, label


@pytest.mark.blackbox
def test_clean_requirement_text_is_unchanged() -> None:
    text = "The system shall lock an account for 15 minutes after 5 failed login attempts."
    result = mask(text)
    assert result.text == text
    assert result.total == 0


@pytest.mark.whitebox
def test_dates_and_requirement_ids_are_not_treated_as_phone_numbers() -> None:
    text = "REQ-0012 was agreed on 2026-11-14 with a 2000 millisecond limit."
    assert mask(text).text == text


@pytest.mark.whitebox
def test_password_key_name_is_kept_and_value_replaced() -> None:
    assert mask("password: Secret99Secret").text == "password: [SECRET]"


@pytest.mark.whitebox
def test_counts_report_what_was_masked() -> None:
    result = mask("a@b.com and c@d.org")
    assert result.counts == {"EMAIL": 2}


@pytest.mark.whitebox
def test_non_string_input_fails_closed() -> None:
    with pytest.raises(MaskingError):
        mask(None)  # type: ignore[arg-type]


@pytest.mark.whitebox
def test_synthetic_emails_can_be_kept_while_real_ones_are_masked() -> None:
    text = "use demo.user@example.test or jane.doe@gmail.com"
    kept = mask(text, keep_synthetic=True)
    assert "demo.user@example.test" in kept.text
    assert "jane.doe@gmail.com" not in kept.text
    assert kept.counts == {"EMAIL": 1}
    assert "demo.user@example.test" not in mask(text).text


@pytest.mark.whitebox
@pytest.mark.parametrize(
    ("value", "safe"),
    [
        ("demo.user@example.test", True),
        ("a@example.com", True),
        ("Test User", True),
        ("john.smith@gmail.com", False),
        ("4111 1111 1111 1111", False),
        ("password=Hunter2Hunter2", False),
    ],
)
def test_is_synthetic_safe(value: str, safe: bool) -> None:
    assert is_synthetic_safe(value) is safe
