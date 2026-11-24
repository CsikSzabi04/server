"""STT benchmark with YOUR voice (AI-1 VOICE, milestone M0 — spec 3.2).

    python scripts/bench_stt.py --record 20     # read 20 commands aloud (mic, VAD-endpointed)
    python scripts/bench_stt.py --dir data/voice/bench_stt/<run>   # re-run on saved recordings
    add --whisper to also run the slow accurate engine (~7.5 s per command)

Recordings are your voice → they stay LOCAL in data/voice/bench_stt/ (gitignored). Delete
the folder whenever you like. Prints per command: engine, time, raw text, lexicon-fixed text,
and word error rate (WER) against the prompt, plus median / p90 summaries.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from auri_jarvis.audio._paths import ROOT, VOICE_DATA, resolve
from auri_jarvis.stt.engines import ParakeetStt, WhisperStt
from auri_jarvis.stt.lexicon import Lexicon

PROMPTS = [
    "Auri, nyisd meg a Visual Studio Code-ot a középső monitoron.",
    "Hány óra van?",
    "Állíts be egy időzítőt huszonöt percre.",
    "Halkítsd le a zenét.",
    "Következő szám.",
    "Nyisd meg a Chrome-ot a bal oldali monitoron.",
    "Mi a helyzet a Server projekttel?",
    "Hangerő harminc százalék.",
    "Jegyezd fel, hogy holnap kilenckor megbeszélés.",
    "Kapcsold be a zenét a YouTube-on.",
    "Mi az a Docker?",
    "Írj egy Python függvényt, ami megfordít egy listát.",
    "Szólj tíz perc múlva.",
    "Állj, elég.",
    "Indítsd el a munka módot.",
    "Mennyi a processzor terhelése?",
    "Nyisd meg az Obsidiant.",
    "Zárd be a Spotifyt.",
    "Hey Auri, mi a mai dátum?",
    "Mi a különbség a let és a const között JavaScriptben?",
]


def wer(ref: str, hyp: str) -> float:
    norm = lambda s: [w for w in "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in s).split()]  # noqa: E731
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        prev, d[0] = d[0], i
        for j, hw in enumerate(h, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (rw != hw))
    return d[len(h)] / max(1, len(r))


def record(n: int, out: Path) -> list[tuple[str, Path]]:
    from auri_jarvis.audio.capture import AudioCapture
    from auri_jarvis.audio.devices import pick_input
    from auri_jarvis.audio.vad import EndpointConfig, Endpointer

    out.mkdir(parents=True, exist_ok=True)
    choice = pick_input("auto")
    cap = AudioCapture(choice.index)
    cap.start()
    ep = Endpointer(EndpointConfig())
    items = []
    try:
        for i, prompt in enumerate(PROMPTS[:n], 1):
            input(f"\n[{i}/{n}] Press Enter, then say:  {prompt}")
            utt = ep.capture(cap.subscribe, max_s=12, start_timeout_s=6, cancel=threading.Event())
            if utt is None:
                print("   (no speech heard — skipped)")
                continue
            path = out / f"{i:02d}.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(16_000)
                w.writeframes((np.clip(utt.pcm, -1, 1) * 32767).astype(np.int16).tobytes())
            (out / f"{i:02d}.txt").write_text(prompt, "utf-8")
            print(f"   recorded {utt.speech_ms} ms")
            items.append((prompt, path))
    finally:
        cap.stop()
    return items


def load_dir(d: Path) -> list[tuple[str, Path]]:
    return [(p.with_suffix(".txt").read_text("utf-8") if p.with_suffix(".txt").is_file() else "", p)
            for p in sorted(d.glob("*.wav"))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", type=int, default=0)
    ap.add_argument("--dir", type=str, default="")
    ap.add_argument("--whisper", action="store_true")
    args = ap.parse_args()
    if args.record:
        items = record(min(args.record, len(PROMPTS)), VOICE_DATA / "bench_stt" / time.strftime("%Y%m%d-%H%M%S"))
    elif args.dir:
        items = load_dir(resolve(args.dir))
    else:
        ap.error("use --record N or --dir PATH")
    lex = Lexicon.load(ROOT / "config/lexicon.yaml")
    engines = [ParakeetStt()] + ([WhisperStt()] if args.whisper else [])
    for eng in engines:
        eng.load()
        times, wers_raw, wers_fix = [], [], []
        print(f"\n=== {eng.name} ===")
        for ref, path in items:
            with wave.open(str(path), "rb") as w:
                pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            t = time.perf_counter()
            raw, _ = eng.transcribe(pcm)
            ms = (time.perf_counter() - t) * 1000
            fixed = lex.correct(raw)
            times.append(ms)
            if ref:
                wers_raw.append(wer(ref, raw))
                wers_fix.append(wer(ref, fixed))
            print(f"{ms:6.0f} ms | {raw}" + (f"\n          → {fixed}" if fixed != raw else ""))
        print(f"time median {statistics.median(times):.0f} ms, max {max(times):.0f} ms")
        if wers_raw:
            print(f"WER raw {statistics.mean(wers_raw):.1%}  → with lexicon {statistics.mean(wers_fix):.1%}")


if __name__ == "__main__":
    main()
