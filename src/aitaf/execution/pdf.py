"""Print an HTML report to PDF with the browser the Execution Engine already owns (FR-32).

The Reporting Engine never imports a browser library (NFR-17: only this package owns
Playwright); it receives this function as a renderer and calls it with the paths.
"""

from __future__ import annotations

from pathlib import Path


def render_html_to_pdf(html: Path, pdf: Path) -> None:
    """Open ``html`` from disk in headless Chromium and save an A4 PDF to ``pdf``."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(html.resolve().as_uri())
                page.pdf(path=str(pdf), format="A4", print_background=True)
            finally:
                browser.close()
    except Exception as exc:  # the browser library raises its own error types
        raise RuntimeError(
            f"the browser could not print the report ({type(exc).__name__})"
        ) from exc
