"""Structured automation plan the model must return (FR-14, FR-16, NFR-10).

Names are restricted to simple identifiers, so a model reply can never smuggle
code into a file name, class name or function name. Everything else is data that
templates embed as string literals.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=200)]

NEEDS_TARGET = {"click", "type", "select", "assert_text", "assert_visible"}
NEEDS_VALUE = {"open", "type", "select", "assert_text"}


class StrategySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["id", "css", "xpath", "text", "role", "attr"]
    value: Text


class LocatorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    primary: StrategySchema
    fallbacks: list[StrategySchema] = Field(default_factory=list, max_length=5)


class StepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["open", "click", "type", "select", "assert_text", "assert_visible"]
    target: Name | None = None
    value: Annotated[str, StringConstraints(max_length=200)] | None = None


class PlanSchema(BaseModel):
    """One page, its named locators, and the steps that use them."""

    model_config = ConfigDict(extra="forbid")

    page: Name
    locators: list[LocatorSchema] = Field(default_factory=list, max_length=30)
    steps: list[StepSchema] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _steps_are_consistent(self) -> PlanSchema:
        names = [loc.name for loc in self.locators]
        if len(set(names)) != len(names):
            raise ValueError("locator names must be unique")
        for step in self.steps:
            if step.action in NEEDS_TARGET and step.target not in names:
                raise ValueError(f"step '{step.action}' needs a target naming a locator")
            if step.action in NEEDS_VALUE and step.value is None:
                raise ValueError(f"step '{step.action}' needs a value")
            if step.action == "open" and not _is_path(step.value):
                raise ValueError("open needs a path starting with '/' and no host")
        return self


def _is_path(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("/") and "://" not in value and ".." not in value
