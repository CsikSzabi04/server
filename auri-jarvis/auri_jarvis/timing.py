"""auri_jarvis.timing — per-turn latency stamps + medians (owner: AI-3).

All stamps use `time.monotonic()` — the same clock as `WakeEvent.t`, so a wake detected on the
PortAudio thread and the reply played on the loop are directly comparable.

Fields of the `timing` event (JARVIS_BUILD §2.3), all in ms, `None` when not applicable:
  wake_ack_ms   wake → acknowledgement audio started
  speech_ms     length of captured speech                  (from Transcript)
  stt_ms        transcription time                         (from Transcript)
  llm_first_ms  request handed to the Mind → first non-empty text delta
  tts_first_ms  first text delta → first reply audio (Mouth.speaking turned on)
  total_ms      wake (or request) → first reply audio  ← the M1 KPI "wake→első szó"
                (no reply audio: wake → end of turn)
  turn_ms       wake → end of turn
Only numbers are logged — never transcript text (privacy.log_transcripts is honoured elsewhere).
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import threading
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

FIELDS = ("wake_ack_ms", "speech_ms", "stt_ms", "llm_first_ms", "tts_first_ms", "total_ms", "turn_ms")


def _ms(a: float | None, b: float | None) -> int | None:
    if a is None or b is None:
        return None
    return max(0, round((b - a) * 1000))


@dataclass
class TurnTiming:
    turn: int
    channel: str
    t0: float = field(default_factory=time.monotonic)  # wake time (WakeEvent.t) or request time
    marks: dict[str, float] = field(default_factory=dict)
    speech_ms: int | None = None
    stt_ms: int | None = None
    path: str | None = None  # route path reported by the Mind (fastpath / llm / …)

    def mark(self, name: str, at: float | None = None) -> None:
        """Record a stamp once (first call wins)."""
        if name not in self.marks:
            self.marks[name] = time.monotonic() if at is None else at

    def has(self, name: str) -> bool:
        return name in self.marks

    def result(self) -> dict[str, Any]:
        m = self.marks
        first_audio = m.get("tts_first")
        end = m.get("end")
        return {
            "turn": self.turn,
            "channel": self.channel,
            "path": self.path,
            "wake_ack_ms": _ms(self.t0, m.get("ack")),
            "speech_ms": self.speech_ms,
            "stt_ms": self.stt_ms,
            "llm_first_ms": _ms(m.get("mind_start"), m.get("llm_first")),
            "tts_first_ms": _ms(m.get("llm_first"), first_audio),
            "total_ms": _ms(self.t0, first_audio if first_audio is not None else end),
            "turn_ms": _ms(self.t0, end),
        }


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile (p in 0..100)."""
    if not values:
        return math.nan
    s = sorted(values)
    k = max(1, math.ceil(p / 100 * len(s)))
    return float(s[k - 1])


def summarize(records: Iterable[dict[str, Any]], fields: Iterable[str] = FIELDS) -> dict[str, dict[str, float]]:
    """{field: {n, median, p90, min, max}} over the records that have the field."""
    recs = list(records)
    out: dict[str, dict[str, float]] = {}
    for f in fields:
        vals = [float(r[f]) for r in recs if isinstance(r.get(f), (int, float))]
        if not vals:
            continue
        out[f] = {
            "n": len(vals),
            "median": float(statistics.median(vals)),
            "p90": percentile(vals, 90),
            "min": min(vals),
            "max": max(vals),
        }
    return out


class TimingLog:
    """Keeps the last N turn results in memory and appends them to data/body/timing.jsonl."""

    def __init__(self, path: Path | None = None, keep: int = 500) -> None:
        self.path = path
        self.records: deque[dict[str, Any]] = deque(maxlen=keep)
        self._lock = threading.Lock()

    def add(self, rec: dict[str, Any]) -> None:
        rec = {**rec, "ts": time.time()}
        with self._lock:
            self.records.append(rec)
            if self.path is not None:
                try:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    with self.path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                except OSError as e:
                    log.warning("timing: cannot append to %s: %s", self.path, e)

    def summary(self) -> dict[str, dict[str, float]]:
        with self._lock:
            return summarize(list(self.records))

    @staticmethod
    def read(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
