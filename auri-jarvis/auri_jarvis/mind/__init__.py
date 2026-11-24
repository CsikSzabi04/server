"""auri_jarvis.mind — LLM, prompts, fast-path, agent, onboarding (owner: AI-2 / MIND).

Factory per contract (JARVIS_BUILD.md 2.1):  create_mind(cfg, emit) -> Mind
The import is lazy so the provider/prompt modules stay importable (and testable)
without the rest of the daemon.
"""

from __future__ import annotations

from typing import Any


def create_mind(cfg: dict[str, Any], emit: Any) -> Any:
    from .core import JarvisMind

    return JarvisMind(cfg, emit)


__all__ = ["create_mind"]
