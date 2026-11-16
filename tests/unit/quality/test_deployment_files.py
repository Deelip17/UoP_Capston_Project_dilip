"""The deployment pack stays consistent with the code (NFR-05, NFR-09, NFR-20, NFR-26)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aitaf.core.config import _FILE_KEYS

ROOT = Path(__file__).resolve().parents[3]
GUIDE = ROOT / "docs" / "user-guide" / "DEPLOYMENT.md"
SETTING_NAMES = {*_FILE_KEYS.values(), "OPENAI_API_KEY"}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.blackbox
def test_the_guide_documents_every_setting_the_program_reads() -> None:
    guide = text(GUIDE)
    assert [name for name in sorted(SETTING_NAMES) if name not in guide] == []


@pytest.mark.blackbox
def test_the_env_template_in_the_guide_names_only_known_settings_and_holds_no_key() -> None:
    block = re.search(r"# \.env\.example.*?```", text(GUIDE), re.S)
    assert block is not None
    names = set(re.findall(r"^([A-Z_0-9]+)=", block.group(0), re.M))
    assert names and names <= SETTING_NAMES
    assert "OPENAI_API_KEY=\n" in block.group(0) and "sk-" not in block.group(0)


@pytest.mark.whitebox
def test_a_committed_env_example_matches_the_known_settings() -> None:
    path = ROOT / ".env.example"
    if not path.exists():
        pytest.skip(".env.example not created yet (template is in DEPLOYMENT.md)")
    names = set(re.findall(r"^([A-Z_0-9]+)=", text(path), re.M))
    assert names <= SETTING_NAMES
    assert not re.search(r"sk-[A-Za-z0-9]", text(path))


@pytest.mark.blackbox
def test_the_dockerfile_runs_as_a_non_root_user_and_bakes_in_no_secret() -> None:
    docker = text(ROOT / "Dockerfile")
    assert re.search(r"^USER (?!root)\S+", docker, re.M)
    assert not re.search(r"(ENV|ARG)\s+OPENAI_API_KEY", docker)
    assert "ENV LLM_PROVIDER=mock" in docker and 'ENTRYPOINT ["aitaf"]' in docker
    assert re.search(r"^FROM python:3\.12", docker, re.M)


@pytest.mark.blackbox
def test_the_docker_context_leaves_out_secrets_local_state_and_the_git_history() -> None:
    ignored = set(text(ROOT / ".dockerignore").split())
    assert {".git", ".venv", ".env", "*.db", ".aitaf_cache", "reports"} <= ignored


@pytest.mark.whitebox
def test_the_dockerfile_copies_what_the_demonstration_needs() -> None:
    docker = text(ROOT / "Dockerfile")
    for needed in ("COPY src ./src", "COPY data ./data", "requirements-report.txt"):
        assert needed in docker
    assert (ROOT / "data" / "requirements" / "shop_requirements.md").exists()
    assert (ROOT / "data" / "dom" / "shop" / "flow.txt").exists()
