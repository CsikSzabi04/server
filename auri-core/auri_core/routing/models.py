"""auri_core.routing.models — which local model sits on which level, and what fits in RAM (08/01).

Numbers: measured where the facts sheet has them (gemma4:e2b 1.9 GB, e4b 2.8 GB, qwen3.5:4b 3.24 GB
NK14 h, embeddinggemma 0.6 GB); coder sizes are the 08/01 §2 estimates (Q4). Unknown models get a
tier from the size tag in their name and an unknown RAM (allowed, the reason says so).
"""

from __future__ import annotations

import re

MODEL_RAM_GB: dict[str, float] = {
    "gemma4:e2b": 1.9,  # measured
    "gemma4:e4b": 2.8,  # measured
    "qwen3.5:4b": 3.24,  # measured (NK14 h)
    "embeddinggemma": 0.6,  # measured
    "qwen2.5-coder:1.5b": 1.2,  # estimate
    "qwen2.5-coder:3b": 2.3,  # estimate
    "qwen2.5-coder:7b": 4.7,  # estimate
    "qwen2.5-coder:14b": 9.0,  # estimate
    "gpt-oss:20b": 14.0,  # estimate
}
MODEL_TIER: dict[str, int] = {
    "gemma4:e2b": 2, "qwen3.5:4b": 2, "qwen2.5-coder:1.5b": 2, "qwen2.5-coder:3b": 2,
    "gemma4:e4b": 3, "qwen2.5-coder:7b": 3, "qwen2.5-coder:14b": 3, "gpt-oss:20b": 3,
}
EMBED_MODELS = frozenset({"embeddinggemma", "nomic-embed-text", "mxbai-embed-large"})
# One more ~4–5 GB model fits next to the always-loaded e2b during the day (08/01 §3, estimate).
DEFAULT_RAM_BUDGET_GB = 5.0
_SIZE = re.compile(r"[:\-_](?:e)?(\d+(?:\.\d+)?)b\b", re.IGNORECASE)


def tier_of(model: str) -> int:
    """2 = small local, 3 = bigger local. From the table, else from the size tag (≤ 4B → 2)."""
    if model in MODEL_TIER:
        return MODEL_TIER[model]
    m = _SIZE.search(model)
    if m:
        return 2 if float(m.group(1)) <= 4.0 else 3
    return 2


def ram_gb(model: str) -> float | None:
    return MODEL_RAM_GB.get(model)


def fits(model: str, lane_model: str, budget_gb: float = DEFAULT_RAM_BUDGET_GB) -> tuple[bool, str]:
    """Can `model` be loaded next to the lane (persona) model? (ok, reason)."""
    if model == lane_model:
        return True, "a sáv modellje"
    gb = ram_gb(model)
    if gb is None:
        return True, "RAM nem mért"
    if gb > budget_gb:
        return False, f"{gb:.1f} GB > {budget_gb:.1f} GB keret"
    return True, f"{gb:.1f} GB"


def usable_models(configured: list[str] | set[str] | tuple[str, ...], lane_model: str,
                  budget_gb: float = DEFAULT_RAM_BUDGET_GB) -> dict[str, str]:
    """Chat/code models we may route to: configured, not an embedder, fits in RAM → {model: why}."""
    out: dict[str, str] = {}
    for m in dict.fromkeys([lane_model, *configured]):  # stable order, lane first
        if not m or m in EMBED_MODELS or "embed" in m:
            continue
        ok, why = fits(m, lane_model, budget_gb)
        if ok:
            out[m] = why
    return out
