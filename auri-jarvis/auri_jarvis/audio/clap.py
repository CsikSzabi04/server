"""Clap detector 2.0 (spec 5.1) — double clap → "clap2", triple clap → "clap3".

Idea (re-implemented, not copied) from hectorg2211/jarvis: energy spike over an adaptive noise
floor, with hysteresis. Added on top, because a bare energy spike also fires on desk knocks,
doors and speech plosives:
  • 10 ms hops (instead of 40 ms) for precise timing
  • spectrum: a clap is broadband — enough energy above 2 kHz (a desk thump is not)
  • decay: a clap dies within ~80 ms (a vowel after a plosive, a door's rumble do not)
  • rhythm: 120–600 ms between claps; a third clap within the window makes it a triple
Pure numpy; feed 16 kHz float32 frames of any size.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

SR = 16_000
HOP = 160  # 10 ms


@dataclass
class ClapConfig:
    spike_ratio: float = 7.0  # onset: hop energy ≥ noise floor × this …
    min_rms: float = 0.01  # … and at least this (float audio)
    min_hf_ratio: float = 0.35  # share of onset energy above 2 kHz
    max_decay_ms: int = 80  # by then energy must have dropped …
    decay_ratio: float = 0.3  # … below this fraction of the peak
    gap_min_ms: int = 120
    gap_max_ms: int = 600
    retrigger_ratio: float = 0.55
    noise_alpha: float = 0.995
    quiet_gate: float = 2.2

    @classmethod
    def from_cfg(cls, c: dict | None) -> ClapConfig:
        c = c or {}
        out = cls()
        for k in cls.__dataclass_fields__:
            if k in c:
                setattr(out, k, type(getattr(out, k))(c[k]))
        if "double_gap_ms" in c:  # spec-style [min, max]
            out.gap_min_ms, out.gap_max_ms = (int(x) for x in c["double_gap_ms"])
        return out


class ClapDetector:
    def __init__(self, cfg: ClapConfig | None = None) -> None:
        self.cfg = cfg or ClapConfig()
        self._buf = np.zeros(0, np.float32)
        self._t = 0  # samples processed
        self._floor = 1e-4
        self._armed = True
        self._cand: dict | None = None  # transient being verified
        self._claps: list[int] = []  # sample times of verified claps
        self._decay_hops = self.cfg.max_decay_ms // 10
        self.last_rejected = ""  # why the last transient was not a clap (debug / calibration)

    def reset(self) -> None:
        self.__init__(self.cfg)

    def feed(self, frame: np.ndarray) -> str | None:
        self._buf = np.concatenate([self._buf, frame.astype(np.float32, copy=False)])
        event = None
        while len(self._buf) >= HOP:
            hop, self._buf = self._buf[:HOP], self._buf[HOP:]
            event = self._hop(hop) or event
            self._t += HOP
        return event

    # ── per 10 ms hop ──────────────────────────────────────────────────────
    def _hop(self, hop: np.ndarray) -> str | None:
        c = self.cfg
        e = float(np.sqrt(np.mean(hop * hop)))
        if e < self._floor * c.quiet_gate:  # learn the room only while it is quiet
            self._floor = max(1e-6, c.noise_alpha * self._floor + (1 - c.noise_alpha) * e)
        thr = max(self._floor * c.spike_ratio, c.min_rms)

        if self._cand is not None:
            self._cand["hops"].append(hop)
            self._cand["e"].append(e)
            if len(self._cand["e"]) >= self._decay_hops + 3:
                if self._verify(self._cand):
                    self._claps.append(self._cand["t"])
                self._cand = None
        elif self._armed and e >= thr:
            self._cand = {"t": self._t, "hops": [hop], "e": [e]}
            self._armed = False
        if e < thr * c.retrigger_ratio:
            self._armed = True
        return self._pattern()

    def _verify(self, cand: dict) -> bool:
        c, energies = self.cfg, cand["e"]
        peak_i = int(np.argmax(energies[:3]))  # the peak is right at the onset
        peak = energies[peak_i]
        after = energies[peak_i + self._decay_hops : peak_i + self._decay_hops + 3]
        if not after or max(after) > c.decay_ratio * peak:
            self.last_rejected = "slow decay (speech / door / music)"
            return False
        onset = np.concatenate(cand["hops"][peak_i : peak_i + 2])  # 20 ms around the peak
        spec = np.abs(np.fft.rfft(onset * np.hanning(len(onset)))) ** 2
        freqs = np.fft.rfftfreq(len(onset), 1 / SR)
        hf = float(spec[freqs >= 2000].sum() / max(spec.sum(), 1e-12))
        if hf < c.min_hf_ratio:
            self.last_rejected = f"too little high-frequency energy ({hf:.2f}) — a thump, not a clap"
            return False
        self.last_rejected = ""
        return True

    def _pattern(self) -> str | None:
        """Decide once the rhythm window after the last clap has passed."""
        c = self.cfg
        if not self._claps or self._cand is not None:
            return None
        if self._t - self._claps[-1] < c.gap_max_ms * SR // 1000:
            return None  # a further clap may still come
        claps, self._claps = self._claps, []
        gaps = [(b - a) * 1000 // SR for a, b in itertools.pairwise(claps)]
        if len(claps) < 2 or not all(c.gap_min_ms <= g <= c.gap_max_ms for g in gaps):
            return None
        return "clap3" if len(claps) >= 3 else "clap2"
