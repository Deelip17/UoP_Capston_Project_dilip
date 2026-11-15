"""Shared kernel for AITAF modules.

Only ``core`` imports third-party clients (pydantic here, the OpenAI SDK in
``core.llm`` later) and the database driver (``core.storage`` later). Other
module packages depend on ``core`` through its public API only (NFR-17).
"""
