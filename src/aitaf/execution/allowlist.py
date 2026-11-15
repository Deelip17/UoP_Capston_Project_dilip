"""Base-URL allow-list check (FR-21, NFR-11, ADR-005).

A run is refused before PyTest or any browser starts if its base URL is not on
the allow-list. The check compares the parsed host (never a substring), refuses
anything but http and https, embedded credentials, odd ports and whitespace, and
never echoes credentials back in the message.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

from aitaf.core.errors import PolicyError


def check_base_url(base_url: str, allowed_hosts: Iterable[str]) -> str:
    """Return the normalised origin (scheme, host, port) or raise :class:`PolicyError`."""
    if any(ch.isspace() or ord(ch) < 32 for ch in base_url):
        raise PolicyError("the base URL must not contain whitespace or control characters")
    try:
        parts = urlsplit(base_url)
        port = parts.port
    except ValueError:
        raise PolicyError("the base URL is not a valid URL (check the port)") from None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise PolicyError("the base URL must start with http:// or https://")
    host = (parts.hostname or "").lower()
    if not host:
        raise PolicyError("the base URL has no host")
    if parts.username is not None or parts.password is not None:
        raise PolicyError("the base URL must not contain credentials")
    allowed = {entry.strip().lower() for entry in allowed_hosts if entry.strip()}
    if host not in allowed:
        raise PolicyError(
            f"host '{host}' is not on the allow-list; the run was not started (FR-21)"
        )
    netloc = f"{host}:{port}" if port else host
    return f"{scheme}://{netloc}"
