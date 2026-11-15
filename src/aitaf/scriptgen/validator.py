"""Static validation of generated scripts by AST allow-list (FR-15, NFR-11).

Generated code is untrusted and runs on the user's machine, so every generated
Python file is parsed and checked before it is saved or run: only a small set of
imports is allowed, dangerous builtins and attributes are rejected, URL literals
must point at allow-listed hosts, and string literals must not hold secrets or
personal data. Each problem comes back as a reason with its line number.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Collection

from aitaf.core.errors import PolicyError
from aitaf.core.masking import find_sensitive

ALLOWED_MODULES = frozenset(
    {
        "__future__",
        "pytest",
        "playwright.sync_api",
        "selenium.webdriver",
        "selenium.webdriver.common.by",
        "selenium.webdriver.support.ui",
    }
)
ALLOWED_PREFIXES = ("locators.", "pages.")
FORBIDDEN_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
    }
)
FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "system",
        "popen",
        "spawn",
        "execv",
        "execve",
        "fork",
        "kill",
        "remove",
        "unlink",
        "rmdir",
        "rmtree",
        "rename",
        "mkdir",
        "makedirs",
        "touch",
        "chmod",
        "write_text",
        "write_bytes",
        "urlopen",
        "connect",
        "request",
        "evaluate",
        "eval_on_selector",
        "add_script_tag",
        "add_init_script",
        "expose_function",
        "execute_script",
        "execute_async_script",
    }
)
_SECRET_NAMES = ("password", "passwd", "secret", "token", "api_key", "apikey")
_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*)://([^/\s:\"'?#@]*)")
_WEB_SCHEMES = frozenset({"http", "https", "ws", "wss", "ftp"})


def _module_allowed(name: str) -> bool:
    return name in ALLOWED_MODULES or name.startswith(ALLOWED_PREFIXES)


def _is_secret_name(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in _SECRET_NAMES)


def _non_empty_str(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and bool(node.value)


def _check_literal(value: str, hosts: set[str]) -> list[str]:
    problems: list[str] = []
    for match in _URL.finditer(value):
        scheme, host = match.group(1).lower(), match.group(2).lower()
        if scheme == "file":
            problems.append("file:// URLs are not allowed")
        elif scheme in _WEB_SCHEMES and host not in hosts:
            problems.append(f"URL host '{host}' is not allow-listed")
    sensitive = find_sensitive(value)
    if sensitive.get("SECRET"):
        problems.append("string literal looks like a secret")
    elif sensitive:
        problems.append("string literal looks like personal data")
    return problems


def validate_script(source: str, allowed_hosts: Collection[str]) -> list[str]:
    """Return the reasons the script is unacceptable; an empty list means it passed."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"line {exc.lineno or 0}: syntax error: {exc.msg}"]

    hosts = {h.lower() for h in allowed_hosts}
    found: list[tuple[int, str]] = []

    def add(node: ast.AST, message: str) -> None:
        found.append((getattr(node, "lineno", 0), message))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _module_allowed(alias.name):
                    add(node, f"import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                add(node, "relative import is not allowed")
            elif module == "selenium":
                if any(alias.name != "webdriver" for alias in node.names):
                    add(node, "import from 'selenium' is limited to 'webdriver'")
            elif not _module_allowed(module):
                add(node, f"import from '{module}' is not allowed")
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES and isinstance(node.ctx, ast.Load):
                add(node, f"use of '{node.id}' is not allowed")
            elif node.id.startswith("__") and node.id.endswith("__"):
                add(node, f"use of dunder name '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                add(node, f"use of '.{node.attr}' is not allowed")
            elif node.attr.startswith("__") and node.attr.endswith("__"):
                add(node, f"access to dunder attribute '{node.attr}' is not allowed")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for message in _check_literal(node.value, hosts):
                add(node, message)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and _is_secret_name(target.id)
                    and _non_empty_str(node.value)
                ):
                    add(node, f"hard-coded secret assigned to '{target.id}'")
        elif isinstance(node, ast.keyword) and node.arg and _is_secret_name(node.arg):
            if _non_empty_str(node.value):
                add(node, f"hard-coded secret passed as '{node.arg}'")

    return [f"line {line}: {message}" for line, message in sorted(found, key=lambda item: item[0])]


def assert_valid(source: str, allowed_hosts: Collection[str], name: str = "script") -> None:
    """Raise :class:`PolicyError` listing every reason if the script fails validation."""
    problems = validate_script(source, allowed_hosts)
    if problems:
        raise PolicyError(f"{name} failed static validation: " + "; ".join(problems))
