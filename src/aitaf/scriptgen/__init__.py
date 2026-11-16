"""Script Generator (FR-12 to FR-16)."""

from aitaf.scriptgen.catalogue import PageCatalogue
from aitaf.scriptgen.files import safe_write
from aitaf.scriptgen.generator import COMPONENT, ScriptGenerationResult, ScriptGenerator
from aitaf.scriptgen.mock_responder import mock_script_responder
from aitaf.scriptgen.validator import assert_valid, validate_script

__all__ = [
    "PageCatalogue",
    "COMPONENT",
    "ScriptGenerationResult",
    "ScriptGenerator",
    "assert_valid",
    "mock_script_responder",
    "safe_write",
    "validate_script",
]
