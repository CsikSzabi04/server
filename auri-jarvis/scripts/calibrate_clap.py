"""Clap calibration with YOUR microphone and room (AI-1 VOICE, M2 — spec 5.1).

    python scripts/calibrate_clap.py              # 30 s room noise, then 10 double claps
    python scripts/calibrate_clap.py --claps 5

Nothing is saved except a small JSON summary in data/voice/clap_calibration.json.
Prints: the room's noise floor, every transient's loudness / high-frequency share / decay,
how many double claps the CURRENT config detects, and suggested values for
`wake.clap` in config/audio.yaml (min_rms, spike_ratio).
"""
from __future__ import annotations

import argparse
import json
import queue
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import yaml

from auri_jarvis.audio._paths import ROOT, VOICE_DATA
from auri_jarvis.audio.capture import AudioCapture
from auri_jarvis.audio.clap import HOP, ClapConfig, ClapDetector
from auri_jarvis.audio.devices import pick_input


def record(cap: AudioCapture, seconds: float) -> np.ndarray:
    q: queue.Queue[np.ndarray] = queue.Queue()
    unsub = cap.subscribe(q.put)
    out, end = [], time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            out.append(q.get(timeout=0.2))
        except queue.Empty:
            pass
    unsub()
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def hop_rms(x: np.ndarray) -> np.ndarray:
    n = len(x) // HOP
    return np.sqrt(np.mean(x[: n * HOP].reshape(n, HOP) ** 2, axis=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claps", type=int, default=10)
    args = ap.parse_args()
    cfg_all = yaml.safe_load((ROOT / "config/audio.yaml").read_text("utf-8"))
    cfg = ClapConfig.from_cfg((cfg_all.get("wake") or {}).get("clap"))
    choice = pick_input((cfg_all.get("audio") or {}).get("input_device", "auto"))
    cap = AudioCapture(choice.index)
    cap.start()
    try:
        input("1/2  Stay quiet for 30 seconds (normal room sounds are fine). Press Enter to start…")
        noise = record(cap, 30)
        e = hop_rms(noise)
        floor, p99 = float(np.median(e)), float(np.percentile(e, 99))
        print(f"     room: median hop RMS {floor:.6f}, 99th percentile {p99:.6f}")

        input(f"2/2  Now double-clap {args.claps}× (one double clap every ~3 s). Press Enter to start…")
        audio = record(cap, args.claps * 3.2 + 1.5)
    finally:
        cap.stop()

    det, found = ClapDetector(cfg), 0
    for i in range(0, len(audio), 1280):
        if det.feed(audio[i:i + 1280]) == "clap2":
            found += 1
    e = hop_rms(audio)
    onsets = [i for i in range(1, len(e)) if e[i] > max(p99 * 3, 1e-4) and e[i - 1] <= max(p99 * 3, 1e-4)]
    peaks = [float(e[i:i + 3].max()) for i in onsets]
    print(f"\n     detected {found}/{args.claps} double claps with the current config "
          f"(min_rms={cfg.min_rms}, spike_ratio={cfg.spike_ratio})")
    if peaks:
        weakest = float(np.percentile(peaks, 10))
        print(f"     transients: {len(peaks)}, onset RMS median {np.median(peaks):.4f}, weakest(10%) {weakest:.4f}")
        suggest_min = round(max(p99 * 4, weakest * 0.5), 4)
        suggest_ratio = round(float(min(12.0, max(4.0, weakest / max(floor, 1e-6) / 3))), 1)
        print(f"\n     suggested config/audio.yaml → wake.clap:  min_rms: {suggest_min}   spike_ratio: {suggest_ratio}")
    else:
        suggest_min = suggest_ratio = None
        print("     no transients found — is the right microphone selected? (scripts/list_devices.py)")
    VOICE_DATA.mkdir(parents=True, exist_ok=True)
    (VOICE_DATA / "clap_calibration.json").write_text(json.dumps({
        "device": choice.name, "noise_median": floor, "noise_p99": p99, "detected": found, "asked": args.claps,
        "suggested_min_rms": suggest_min, "suggested_spike_ratio": suggest_ratio, "at": time.time(),
    }, indent=2), "utf-8")


if __name__ == "__main__":
    main()
