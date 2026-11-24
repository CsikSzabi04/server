"""List audio devices and show which microphone Auri would pick (AI-1 VOICE).

    python scripts/list_devices.py            # list + auto choice (records 0.4 s per probed mic, nothing saved)
    python scripts/list_devices.py --all      # include every host API (MME, DirectSound, WASAPI, WDM-KS)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sounddevice as sd

from auri_jarvis.audio.devices import pick_input


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="show all host APIs, not only MME")
    args = ap.parse_args()
    default_in, default_out = sd.default.device
    for i, d in enumerate(sd.query_devices()):
        api = sd.query_hostapis(d["hostapi"])["name"]
        if not args.all and api != "MME":
            continue
        kind = ("IN " if d["max_input_channels"] else "   ") + ("OUT" if d["max_output_channels"] else "   ")
        mark = " *default in" if i == default_in else (" *default out" if i == default_out else "")
        print(f"[{i:2d}] {kind} {api:18s} {int(d['default_samplerate']):6d} Hz  {d['name']}{mark}")
    choice = pick_input("auto")
    print(f"\nAuri would listen on [{choice.index}] {choice.name} ({choice.hostapi}) — {choice.reason}, "
          f"probe rms={choice.probe_rms}")
    print("Override with audio.input_device in config/audio.yaml or the JARVIS_INPUT_DEVICE env var.")


if __name__ == "__main__":
    main()
