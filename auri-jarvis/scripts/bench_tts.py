"""TTS latency benchmark (AI-1 VOICE): in-process Piper, after warm-up.

    python scripts/bench_tts.py               # silent (no audio played): synthesis timing only
    python scripts/bench_tts.py --play        # also play through the speakers (audible!)

Reports cold load/warm-up and, per sentence, time to first audio + total synthesis time,
with median / p90 over all runs.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auri_jarvis.audio._paths import ROOT
from auri_jarvis.tts.piper_tts import PiperEngine
from auri_jarvis.tts.textclean import clean_for_tts

SENTENCES = [
    "Igen?",
    "Máris, megnyitom a böngészőt a bal oldali monitoron.",
    "Most 22:15 van, és két emlékeztetőd van mára.",
    "Az időzítőt huszonöt percre állítottam, szólok, ha lejárt.",
    "A Docker egy konténerbe csomagolja az alkalmazást és a függőségeit.",
    "The build finished successfully, all tests are green.",
]


def p90(xs: list[float]) -> float:
    return sorted(xs)[max(0, round(0.9 * len(xs)) - 1)]


def check_elevenlabs_key() -> None:
    """Is the key in .env valid and allowed to speak? Never prints the key."""
    from dotenv import dotenv_values

    from auri_jarvis.audio._paths import VOICE_DATA
    from auri_jarvis.tts.credits import CreditLedger
    from auri_jarvis.tts.elevenlabs import ElevenLabsError, ElevenLabsTts

    env = dotenv_values(ROOT / ".env")
    key = (env.get("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        print("✗ ELEVENLABS_API_KEY is empty in auri-jarvis/.env → Auri uses local Piper only.")
        return
    el = ElevenLabsTts(key, {"daniel": env.get("ELEVENLABS_VOICE_ID") or "onwK4e9ZLuTAKqWW03F9"})
    t = time.perf_counter()
    try:
        n = sum(len(pcm) for pcm, _ in el.synthesize("Szia.", "daniel", "hu"))
    except ElevenLabsError as e:
        print(f"✗ The key does not work: {e}")
        return
    used = CreditLedger(VOICE_DATA / "credits.json", 0).add(el.last_cost)
    print(f"✓ Key OK (…{key[-4:]}): {n / 22_050:.2f} s audio in {(time.perf_counter() - t) * 1000:.0f} ms, "
          f"{el.last_cost} credits (booked; this month: {used})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--check-key", action="store_true",
                    help="only test the ElevenLabs key in .env: one silent 'Szia.' (~2 credits)")
    args = ap.parse_args()
    if args.check_key:
        check_elevenlabs_key()
        return
    eng = PiperEngine({"hu": ROOT / "models/piper/hu_HU-imre-medium.onnx",
                       "en": ROOT / "models/piper/en_GB-alan-medium.onnx"})
    t = time.perf_counter()
    eng.warmup(("hu", "en"))
    print(f"cold load + warm-up (hu+en): {time.perf_counter() - t:.2f} s")
    firsts, totals, audio_s = [], [], []
    for _ in range(args.runs):
        for s in SENTENCES:
            lang = "en" if s.startswith("The ") else "hu"
            text = clean_for_tts(s, lang)
            t = time.perf_counter()
            first, n, rate = None, 0, 22050
            chunks = []
            for pcm, sr in eng.synthesize(text, lang):
                rate = sr
                if first is None:
                    first = (time.perf_counter() - t) * 1000
                n += len(pcm)
                chunks.append(pcm)
            firsts.append(first)
            totals.append((time.perf_counter() - t) * 1000)
            audio_s.append(n / rate)
            if args.play:
                import numpy as np
                import sounddevice as sd

                sd.play(np.concatenate(chunks), rate)
                sd.wait()
    print(f"sentences: {len(firsts)}  audio per sentence: {statistics.mean(audio_s):.2f} s avg")
    print(f"first audio  median {statistics.median(firsts):.0f} ms   p90 {p90(firsts):.0f} ms   max {max(firsts):.0f} ms")
    print(f"total synth  median {statistics.median(totals):.0f} ms   p90 {p90(totals):.0f} ms")
    print(f"real-time factor ≈ {sum(totals) / 1000 / sum(audio_s):.3f} (lower is faster)")


if __name__ == "__main__":
    main()
