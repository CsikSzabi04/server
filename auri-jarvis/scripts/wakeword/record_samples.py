"""Record YOUR wake-word samples (AI-1 VOICE, M2 gate + M5 training data).

    python scripts/wakeword/record_samples.py            # 30× "Hey Auri", 10× "Hey Jarvis", 60 s normal talk
    python scripts/wakeword/record_samples.py --auri 10 --jarvis 0 --negative-s 0   # a quick short round
    python scripts/wakeword/record_samples.py --dry-run  # only show the prompts

Each prompt: press Enter, say the phrase; the recording stops by itself when you are silent.
Files stay LOCAL (your voice): data/voice/wake_user/{hey_auri,hey_jarvis,negative}/*.wav (gitignored).
Afterwards measure:  python scripts/bench_wake.py --user-dir data/voice/wake_user
"""
from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from auri_jarvis.audio._paths import VOICE_DATA

# Variety matters more than count: distance, loudness, speed, with/without a command.
HINTS = [
    "normál hangon, közelről", "normál hangon, 2–3 méterről", "halkabban", "hangosabban",
    "gyorsan, egy szuszra", "lassan, tagoltan", "utána rögtön egy kérdéssel (pl. „…, hány óra van?”)",
    "félig elfordulva a mikrofontól", "fáradt, laza hangon", "mintha a szoba másik végéből szólnál",
]


def save(path: Path, pcm: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes((np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auri", type=int, default=30)
    ap.add_argument("--jarvis", type=int, default=10)
    ap.add_argument("--negative-s", type=int, default=60)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = VOICE_DATA / "wake_user"
    plan = [("hey_auri", "Hey Auri", args.auri), ("hey_jarvis", "Hey Jarvis", args.jarvis)]
    if args.dry_run:
        for _, phrase, n in plan:
            for i in range(n):
                print(f"{phrase:10s} — {HINTS[i % len(HINTS)]}")
        print(f"negative: {args.negative_s} s normal talk WITHOUT the wake words")
        return

    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.devices import pick_input
    from auri_jarvis.audio.vad import EndpointConfig, Endpointer

    choice = pick_input("auto")
    print(f"Mikrofon: {choice.name}\n")
    cap = AudioCapture(choice.index)
    cap.start()
    ep = Endpointer(EndpointConfig(end_silence_ms=500))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        for folder, phrase, n in plan:
            done = 0
            while done < n:
                hint = HINTS[done % len(HINTS)]
                input(f"[{phrase} {done + 1}/{n}] Enter, majd mondd: „{phrase}” — {hint}")
                utt = ep.capture(cap.subscribe, max_s=5, start_timeout_s=6, cancel=threading.Event())
                if utt is None:
                    print("   nem hallottam semmit — még egyszer")
                    continue
                save(out / folder / f"{stamp}-{done + 1:02d}.wav", utt.pcm)
                print(f"   ✓ {utt.speech_ms} ms")
                done += 1
        if args.negative_s > 0:
            input(f"\nUtolsó: Enter, majd beszélj {args.negative_s} mp-ig bármiről (vagy indíts egy videót) — "
                  "de NE mondd, hogy Auri vagy Jarvis.")
            q: queue.Queue[np.ndarray] = queue.Queue()
            unsub = cap.subscribe(q.put)
            time.sleep(args.negative_s)
            unsub()
            frames = [q.get() for _ in range(q.qsize())]
            if frames:
                save(out / "negative" / f"{stamp}-talk.wav", np.concatenate(frames))
                print("   ✓ mentve")
    finally:
        cap.stop()
    print(f"\nKész: {out}\nMérés:  python scripts/bench_wake.py --user-dir data/voice/wake_user")


if __name__ == "__main__":
    main()
