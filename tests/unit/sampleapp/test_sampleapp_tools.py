"""Snapshot writer, command line and server edge cases (FR-38, NFR-10, NFR-11)."""

from __future__ import annotations

import http.client
from pathlib import Path

import pytest

from aitaf.sampleapp import ShopServer, write_snapshots
from aitaf.sampleapp.__main__ import main
from aitaf.sampleapp.elements import PAGES
from aitaf.sampleapp.pages import render_page
from aitaf.sampleapp.server import DEMO_PASSWORD, DEMO_USER


def raw_post(shop: ShopServer, path: str, body: bytes, length: str | None = None) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", shop.port, timeout=5)
    try:
        connection.putrequest("POST", path)
        connection.putheader("Content-Type", "application/x-www-form-urlencoded")
        connection.putheader("Content-Length", length if length is not None else str(len(body)))
        connection.endheaders(body)
        return connection.getresponse().status
    finally:
        connection.close()


@pytest.mark.blackbox
def test_snapshots_write_one_file_per_page_matching_the_renderer(tmp_path: Path) -> None:
    paths = write_snapshots(tmp_path / "out", ["M-login_submit-id"])
    assert [p.name for p in paths] == [f"{page}.html" for page in PAGES]
    login = (tmp_path / "out" / "login.html").read_text(encoding="utf-8")
    assert login == render_page("login", ["M-login_submit-id"])


@pytest.mark.blackbox
def test_command_line_lists_the_catalogue(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert out.count("M-") == 37 and "M-login_submit-id" in out


@pytest.mark.blackbox
def test_command_line_writes_snapshots(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["snapshot", "--out", str(tmp_path), "--mutation", "M-username-class"]) == 0
    assert len(list(tmp_path.glob("*.html"))) == 5
    assert "login.html" in capsys.readouterr().out


@pytest.mark.whitebox
def test_command_line_rejects_an_unknown_mutation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["snapshot", "--out", str(tmp_path), "--mutation", "M-nothing-id"]) == 2
    assert "unknown mutation" in capsys.readouterr().err


@pytest.mark.whitebox
def test_serve_prints_the_address_and_stops_on_interrupt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def interrupt(_seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("aitaf.sampleapp.__main__.time.sleep", interrupt)
    assert main(["serve", "--port", "0"]) == 0
    out = capsys.readouterr().out
    assert "http://127.0.0.1:" in out and DEMO_USER in out and DEMO_PASSWORD in out


@pytest.mark.whitebox
@pytest.mark.parametrize("length", ["not-a-number", "-5", "20000"])
def test_a_bad_or_oversized_body_is_refused(length: str) -> None:
    with ShopServer() as shop:
        assert raw_post(shop, "/login", b"username=x", length=length) in (400, 413)


@pytest.mark.whitebox
def test_posts_need_a_login_and_unknown_post_routes_are_refused() -> None:
    with ShopServer() as shop:
        assert raw_post(shop, "/cart/add", b"sku=backpack") == 200  # shows the login page
        raw_post(shop, "/login", f"username={DEMO_USER}&password={DEMO_PASSWORD}".encode())
        assert raw_post(shop, "/admin", b"x=1") == 404


@pytest.mark.whitebox
def test_the_server_refuses_to_bind_to_a_public_address() -> None:
    with pytest.raises(ValueError):
        ShopServer(host="0.0.0.0")  # noqa: S104 - proves the refusal


@pytest.mark.whitebox
def test_port_is_unavailable_before_the_server_starts() -> None:
    with pytest.raises(RuntimeError):
        _ = ShopServer().port
