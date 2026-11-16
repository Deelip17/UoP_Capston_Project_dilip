"""Run configuration for the Execution Engine (FR-17, FR-20, FR-21).

One frozen record holds everything a run needs: where the scripts are, which base
URL and hosts are allowed, the driver, headless mode, timeouts, retries and
parallel workers. Out-of-range values are rejected at construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunConfig(BaseModel):
    """Settings for one execution run (all limits are bounded)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scripts_dir: Path
    base_url: str = Field(min_length=1)
    allowed_hosts: tuple[str, ...] = Field(min_length=1)
    evidence_dir: Path
    driver: Literal["playwright", "selenium"] = "playwright"
    headless: bool = True
    timeout_ms: int = Field(default=10_000, ge=100, le=300_000)
    retries: int = Field(default=0, ge=0, le=5)
    workers: int = Field(default=1, ge=1, le=8)
    checkpoints: bool = False
    run_timeout_s: int = Field(default=600, ge=1, le=3600)
    healing: bool = False
    max_heal_passes: int = Field(default=5, ge=1, le=20)

    @field_validator("scripts_dir", "evidence_dir")
    @classmethod
    def _absolute(cls, folder: Path) -> Path:
        """PyTest runs from inside the scripts folder, so a relative path would point nowhere."""
        return folder.resolve()

    @field_validator("allowed_hosts")
    @classmethod
    def _clean_hosts(cls, hosts: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(host.strip().lower() for host in hosts)
        if not all(cleaned):
            raise ValueError("allowed_hosts must not contain blank entries")
        return cleaned
