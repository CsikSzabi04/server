"""auri_core.routing — measured data for the P6 router (owner: AI-1). The router itself: `auri_core.router`."""

from .models import DEFAULT_RAM_BUDGET_GB, MODEL_RAM_GB, MODEL_TIER, fits, ram_gb, tier_of, usable_models
from .stats import (
    MIN_N,
    MODES,
    CellStats,
    Record,
    StatsTable,
    build_table,
    load_bench_records,
    record_from_bench,
    wilson_lower,
)

__all__ = [
    "DEFAULT_RAM_BUDGET_GB", "MIN_N", "MODEL_RAM_GB", "MODEL_TIER", "MODES", "CellStats", "Record", "StatsTable",
    "build_table", "fits", "load_bench_records", "ram_gb", "record_from_bench", "tier_of", "usable_models",
    "wilson_lower",
]
