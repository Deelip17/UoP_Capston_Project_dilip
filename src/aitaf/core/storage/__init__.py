"""Persistence behind a repository interface (FR-19, NFR-07, NFR-24)."""

from aitaf.core.storage.memory import InMemoryRepository
from aitaf.core.storage.repository import Repository
from aitaf.core.storage.sqlite import SqliteRepository

__all__ = ["InMemoryRepository", "Repository", "SqliteRepository"]
