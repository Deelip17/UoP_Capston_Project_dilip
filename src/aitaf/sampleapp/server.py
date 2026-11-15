"""A tiny local web shop used as the system under test (FR-38, FR-21, NFR-11).

Standard library only. It binds to the loopback address, so it can be placed on
the Execution Engine's host allow-list and is not reachable from other machines.
There is one shared session (single user, in memory): this is a test fixture,
not a web application. Credentials are synthetic (ADR-005). Started with
mutation IDs, it serves those mutated pages so self-healing can be evaluated
reproducibly.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from urllib.parse import parse_qs, urlsplit

from aitaf.sampleapp.mutations import get_mutation
from aitaf.sampleapp.pages import PRODUCTS, render_page

DEMO_USER = "demo@example.com"
DEMO_PASSWORD = "demo-pass"
MAX_BODY = 10_000
_LOOPBACK = frozenset({"127.0.0.1", "localhost"})


class _State:
    def __init__(self) -> None:
        self.logged_in = False
        self.cart: list[str] = []
        self.lock = threading.Lock()


def _handler_for(state: _State, mutations: tuple[str, ...]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "DemoShop/1.0"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            """Stay silent: the server is a fixture and must not clutter test output."""

        # ---------------------------------------------------------- helpers
        def _send(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _redirect(self, location: str) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _form(self) -> dict[str, str] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            if length < 0 or length > MAX_BODY:
                return None
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            return {key: values[0] for key, values in parse_qs(raw).items()}

        def _page(self, page: str, status: int = 200, **kwargs: object) -> None:
            self._send(status, render_page(page, mutations, **kwargs))  # type: ignore[arg-type]

        # ----------------------------------------------------------- routes
        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            with state.lock:
                if path in ("/", "/login"):
                    self._page("login")
                elif path in ("/products", "/cart", "/checkout") and not state.logged_in:
                    self._page("login")
                elif path == "/products":
                    self._page("products")
                elif path == "/cart":
                    self._page("cart", cart=tuple(state.cart))
                elif path == "/checkout":
                    self._page("checkout")
                else:
                    self._send(404, "<!DOCTYPE html><title>Not found</title><h1>Not found</h1>\n")

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            form = self._form()
            if form is None:
                self._send(413, "<!DOCTYPE html><title>Too large</title><h1>Bad request</h1>\n")
                return
            with state.lock:
                if path == "/login":
                    ok = form.get("username") == DEMO_USER and form.get("password") == DEMO_PASSWORD
                    state.logged_in = ok
                    if ok:
                        self._page("products")
                    else:
                        self._page("login", error="Invalid email or password")
                elif not state.logged_in:
                    self._page("login")
                elif path in ("/cart/add", "/cart/remove"):
                    self._cart(path, form.get("sku", ""))
                elif path == "/checkout":
                    self._checkout(form.get("name", "").strip())
                else:
                    self._send(404, "<!DOCTYPE html><title>Not found</title><h1>Not found</h1>\n")

        def _cart(self, path: str, sku: str) -> None:
            if sku not in PRODUCTS:
                self._send(
                    400, "<!DOCTYPE html><title>Bad request</title><h1>Unknown product</h1>\n"
                )
                return
            if path == "/cart/add":
                state.cart.append(sku)
                self._page("products")
            else:
                if sku in state.cart:
                    state.cart.remove(sku)
                self._page("cart", cart=tuple(state.cart))

        def _checkout(self, name: str) -> None:
            if not name or len(name) > 80:
                self._send(400, "<!DOCTYPE html><title>Bad request</title><h1>Name required</h1>\n")
                return
            if not state.cart:
                self._send(400, "<!DOCTYPE html><title>Bad request</title><h1>Cart is empty</h1>\n")
                return
            state.cart.clear()
            self._page("confirmation")

    return Handler


class ShopServer:
    """Run the shop on a free loopback port; use as a context manager."""

    def __init__(
        self, mutations: Iterable[str] = (), host: str = "127.0.0.1", port: int = 0
    ) -> None:
        if host not in _LOOPBACK:
            raise ValueError("the sample shop only binds to the loopback address")
        self._mutations = tuple(mutations)
        for mutation_id in self._mutations:
            get_mutation(mutation_id)  # KeyError for an unknown mutation, before binding
        self._host = host
        self._requested_port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        if self._httpd is None:
            raise RuntimeError("the server is not running")
        return int(self._httpd.server_address[1])

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self.port}"

    def start(self) -> None:
        handler = _handler_for(_State(), self._mutations)
        self._httpd = ThreadingHTTPServer((self._host, self._requested_port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> ShopServer:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()
