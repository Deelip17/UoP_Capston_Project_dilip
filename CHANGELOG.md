# Changelog

Format: Keep a Changelog. Versions follow Semantic Versioning.

## [Unreleased]

### Added
- Repository skeleton, README, contributing guide and pull-request template.
- Architecture, requirements and Git strategy documentation (Unit 3 baseline).
- Unit 4 CI workflow (`.github/workflows/ci.yml`): lint, test matrix (Ubuntu, Windows), security audit, build.
- Unit 5 slice 1 thin core: `aitaf.core.errors`, `aitaf.core.config`, `aitaf.core.logging`, `aitaf.core.models` (AnalyzedRequirement, TestCase) with 30 unit tests at 98% coverage. Pydantic 2.14.3 added as a runtime dependency (ADR-032). Pytest `blackbox` and `whitebox` markers added for Unit 5 evidence.
