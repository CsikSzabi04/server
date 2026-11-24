"""Monthly ElevenLabs credit ledger (spec 5.7). The key cannot read the account quota
(no user_read permission), so we book the `character-cost` header of every response and
switch to local Piper once the monthly budget is used up."""

from __future__ import annotations

import json
import math
import os
import threading
import time
from pathlib import Path

CREDITS_PER_CHAR_ESTIMATE = 0.5  # flash v2.5 measured ≈ 0.4; estimate a bit high on purpose


class CreditLedger:
    def __init__(self, path: Path, monthly_budget: int) -> None:
        self.path = Path(path)
        self.budget = int(monthly_budget)
        self._lock = threading.Lock()

    @staticmethod
    def _month() -> str:
        return time.strftime("%Y-%m")

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            data = {}
        if data.get("month") != self._month():
            data = {"month": self._month(), "used": 0}
        return data

    @property
    def used(self) -> int:
        with self._lock:
            return int(self._load()["used"])

    def allows(self, text: str) -> bool:
        return self.used + math.ceil(len(text) * CREDITS_PER_CHAR_ESTIMATE) <= self.budget

    def add(self, credits: int) -> int:
        with self._lock:
            data = self._load()
            data["used"] = int(data["used"]) + max(0, int(credits))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic replace: the AuriGPT web dev server (Node) may book into the same file.
            tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(data), "utf-8")
            os.replace(tmp, self.path)
            return data["used"]
