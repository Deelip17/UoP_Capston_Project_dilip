"""The PDF version of a report, printed by headless Chromium (FR-32).

Needs Chromium (``playwright install chromium``); skipped when it is not available.
Excluded from the default run (marker ``integration``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pipeline_records import EXEC, SOURCE, seeded_repo

from aitaf.execution.pdf import render_html_to_pdf
from aitaf.reporting import build_report, write_report

pytestmark = [pytest.mark.integration, pytest.mark.blackbox]


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            playwright.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


def test_the_html_report_is_printed_to_a_real_pdf(tmp_path: Path) -> None:
    if not _chromium_available():
        pytest.skip("Chromium is not installed (playwright install chromium)")
    data = build_report(seeded_repo(), EXEC, SOURCE)
    files = write_report(data, tmp_path / "out", None, pdf_renderer=render_html_to_pdf)
    assert files.pdf is not None
    content = files.pdf.read_bytes()
    assert content.startswith(b"%PDF") and len(content) > 5_000
