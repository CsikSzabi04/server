"""Microphone / speaker selection.

Order (re-implemented idea from hectorg2211/jarvis, not copied):
  1. explicit spec (config `audio.input_device` or env JARVIS_INPUT_DEVICE): index or name substring
  2. the system default input — unless it is dead (no signal at all)
  3. the loudest working input
MME is preferred: on Windows it resamples to 16 kHz for us, so no extra resampler is needed.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass

import numpy as np
import sounddevice as sd

from ._paths import VOICE_DATA

log = logging.getLogger("auri.voice.devices")

DEAD_RMS = 1e-5  # an input that is literally silent (unplugged / muted) — not "a quiet room"
PROBE_S = 0.4


@dataclass
class DeviceChoice:
    index: int
    name: str
    hostapi: str
    probe_rms: float | None
    reason: str


def _hostapi_name(dev: dict) -> str:
    return sd.query_hostapis(dev["hostapi"])["name"]


def list_inputs() -> list[tuple[int, dict]]:
    return [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]


def list_outputs() -> list[tuple[int, dict]]:
    return [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_output_channels"] > 0]


def probe_rms(index: int, seconds: float = PROBE_S) -> float | None:
    """Record a moment from the device; None if it cannot be opened."""
    try:
        rec = sd.rec(int(16_000 * seconds), samplerate=16_000, channels=1, dtype="float32", device=index)
        sd.wait()
        return float(np.sqrt(np.mean(np.square(rec))))
    except Exception:  # PortAudioError, invalid sample rate, device busy …
        return None


def _resolve_spec(spec: str) -> int | None:
    spec = spec.strip()
    if spec.isdigit():
        return int(spec)
    needle = spec.lower()
    inputs = list_inputs()
    # prefer MME (resamples for us), then any host API
    for i, d in sorted(inputs, key=lambda t: _hostapi_name(t[1]) != "MME"):
        if needle in d["name"].lower():
            return i
    return None


def pick_input(spec: str | int | None = None) -> DeviceChoice:
    """Choose the microphone (see module doc). Never raises if any input exists."""
    spec = os.environ.get("JARVIS_INPUT_DEVICE") or spec
    if spec not in (None, "", "auto"):
        idx = _resolve_spec(str(spec))
        if idx is not None:
            d = sd.query_devices(idx)
            return _remember(DeviceChoice(idx, d["name"], _hostapi_name(d), probe_rms(idx), f"config: {spec}"))
        log.warning("No input device matches %r — falling back to auto", spec)

    default = sd.default.device[0]
    if default is not None and default >= 0:
        rms = probe_rms(default)
        if rms is not None and rms > DEAD_RMS:
            d = sd.query_devices(default)
            return _remember(DeviceChoice(default, d["name"], _hostapi_name(d), rms, "system default"))
        log.warning("Default input %s looks dead (rms=%s) — scanning", default, rms)

    best: DeviceChoice | None = None
    for i, d in list_inputs():
        if _hostapi_name(d) != "MME":
            continue
        rms = probe_rms(i)
        if rms is not None and (best is None or rms > (best.probe_rms or 0)):
            best = DeviceChoice(i, d["name"], "MME", rms, "loudest working input")
    if best is not None:
        return _remember(best)
    i, d = list_inputs()[0]
    return _remember(DeviceChoice(i, d["name"], _hostapi_name(d), None, "first input (nothing else worked)"))


def _remember(choice: DeviceChoice) -> DeviceChoice:
    log.info(
        "Microphone [%d] %s (%s, rms=%s) — %s",
        choice.index,
        choice.name,
        choice.hostapi,
        None if choice.probe_rms is None else f"{choice.probe_rms:.5f}",
        choice.reason,
    )
    try:
        VOICE_DATA.mkdir(parents=True, exist_ok=True)
        (VOICE_DATA / "device.json").write_text(
            json.dumps({**asdict(choice), "chosen_at": time.time()}, ensure_ascii=False, indent=2), "utf-8"
        )
    except OSError:
        pass
    return choice
