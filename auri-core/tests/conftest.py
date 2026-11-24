"""Shared fixtures (owner: AI-3). Tests run without Ollama and without internet."""

from __future__ import annotations

import pytest

from auri_core.config import Config, build_config


@pytest.fixture
def cfg(tmp_path) -> Config:
    return build_config({"AURI_CORE_DATA_DIR": str(tmp_path / "data"), "LOCALAPPDATA": str(tmp_path / "la")})


@pytest.fixture
def store():
    from auri_core.store import SqliteKnowledgeStore

    s = SqliteKnowledgeStore(":memory:")
    yield s
    s.close()
