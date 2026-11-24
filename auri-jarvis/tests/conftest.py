"""Shared pytest setup (owner: AI-3).

- pytest-asyncio runs in auto mode (pyproject.toml), so `async def test_…` just works.
- `@pytest.mark.manual` tests (real side effects: apps, audio, ElevenLabs) are deselected by
  default (`-m "not manual"` in addopts); run them by hand with `pytest -m manual`.
- Fixtures here are generic; zone-specific fixtures live in tests/<zone>/conftest.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # make `import auri_jarvis` work without installing the package
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def project_root() -> Path:
    return ROOT


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """A temp project root with a copy of the real jarvis.yaml and an empty .env."""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "jarvis.yaml").write_text((ROOT / "config" / "jarvis.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / ".env").write_text("", encoding="utf-8")
    return tmp_path
