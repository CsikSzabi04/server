"""Wake-word benchmark (AI-1 VOICE, M2 — spec 5.1 gate: ≥ 90 % recall, ≤ 1 false wake / hour).

    python scripts/bench_wake.py                       # synthetic data (Piper voices) — silent, no mic
    python scripts/bench_wake.py --user-dir DIR        # + your own recordings (*.wav, 16 kHz mono):
                                                       #   DIR/hey_auri/*.wav, DIR/hey_jarvis/*.wav, DIR/negative/*.wav

Positives: several voices × phrasings × speeds × (clean / noisy / far). Negatives: near-miss words
("Aurora", "Laura", "hey Siri"…), everyday HU/EN sentences, and real English speech + music.
Reports per engine: recall, false wakes per hour of negative audio, CPU ms per 80 ms frame.
Synthetic speech is easier than a real room — the user's recordings are the real gate.
"""
from __future__ import annotations

import argparse
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from auri_jarvis.audio._paths import ROOT, VOICE_DATA, resolve

SR, FRAME = 16_000, 1_280
VOICES = {
    "imre": ("hu", ROOT / "models/piper/hu_HU-imre-medium.onnx"),
    "berta": ("hu", ROOT / "models/piper/hu_HU-berta-medium.onnx"),
    "anna": ("hu", ROOT.parent / "PublicFreeAI/Piper/voices/hu_HU-anna-medium.onnx"),
    "alan": ("en", ROOT / "models/piper/en_GB-alan-medium.onnx"),
    "ryan": ("en", ROOT / "models/piper/en_US-ryan-medium.onnx"),
}
POSITIVE = {
    "hey_auri": {
        "hu": ["Hey Auri!", "Hé, Auri!", "Hej Auri, hány óra van?", "Hey Auri, nyisd meg a böngészőt.",
               "Auri, kapcsold be a zenét."],
        "en": ["Hey Auri!", "Hey Owry, what time is it?", "Hey Auri, open the browser."],
    },
    "hey_jarvis": {
        "hu": ["Hey Jarvis!", "Hey Jarvis, hány óra van?"],
        "en": ["Hey Jarvis!", "Hey Jarvis, what's the time?"],
    },
}
NEGATIVE = {
    "hu": ["Laura, gyere ide egy percre.", "Az Aurora fényei gyönyörűek voltak.", "Hé, Ottó, mi újság?",
           "Hej, de jó ez a zene!", "Holnap auditra megyünk a céggel.", "Az óra pontosan hétkor csörgött.",
           "Nyisd ki az ablakot, kérlek.", "A Jóska ma nem jön dolgozni.", "Hány órakor kezdődik a meccs?",
           "Ez a kód még mindig nem fordul le.", "A házi feladatot holnapra kell megírni.",
           "Mária szerint a vonat késik.", "Hívd fel anyát, ha hazaértél.", "A kávé már kihűlt."],
    "en": ["Hey Siri, set a timer.", "Laura is coming over tonight.", "The aurora was amazing last night.",
           "Hey, how are you doing?", "We have an audit tomorrow morning.", "Hey Jervis, nice to meet you.",
           "Our server needs a reboot.", "I will call you in an hour.", "Jarvis Cocker sang that song.",
           "Open the window, please.", "The meeting moved to Friday.", "Hurry, we are late!"],
}


def synth(path: Path, text: str, speed: float) -> np.ndarray:
    import soxr
    from piper import PiperVoice, SynthesisConfig

    v = synth.cache.get(path) or synth.cache.setdefault(path, PiperVoice.load(path))
    parts = list(v.synthesize(text, syn_config=SynthesisConfig(length_scale=speed)))
    pcm = np.concatenate([np.frombuffer(c.audio_int16_bytes, np.int16) for c in parts]).astype(np.float32) / 32768
    return soxr.resample(pcm, parts[0].sample_rate, SR).astype(np.float32)


synth.cache = {}


def augment(x: np.ndarray, kind: str, rng: np.random.Generator) -> np.ndarray:
    pad = lambda s: rng.normal(0, 0.002, int(SR * s)).astype(np.float32)  # noqa: E731 — quiet room
    y = np.concatenate([pad(0.6), x, pad(1.0)])
    if kind == "noisy":  # ~15 dB SNR
        y = y + rng.normal(0, np.sqrt(np.mean(x ** 2)) / 5.6, len(y)).astype(np.float32)
    elif kind == "far":  # quieter + noise (~20 dB SNR of the quieter signal)
        y = 0.25 * y
        y = y + rng.normal(0, np.sqrt(np.mean((0.25 * x) ** 2)) / 10, len(y)).astype(np.float32)
    return np.clip(y, -1, 1)


def read_wav(p: Path) -> np.ndarray:
    with wave.open(str(p), "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, f"{p}: need 16 kHz mono"
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def build(word: str, user_dir: Path | None, rng) -> tuple[list[tuple[str, np.ndarray]], np.ndarray]:
    pos = []
    for name, (lang, path) in VOICES.items():
        if not path.is_file():
            continue
        for text in POSITIVE[word][lang]:
            for speed in (0.85, 1.0, 1.2):
                clean = synth(path, text, speed)
                for kind in ("clean", "noisy", "far"):
                    pos.append((f"{name}|{speed}|{kind}|{text}", augment(clean, kind, rng)))
    neg_parts = []
    for _name, (lang, path) in VOICES.items():
        if path.is_file():
            for text in NEGATIVE[lang]:
                neg_parts.append(augment(synth(path, text, 1.0), "clean", rng))
    other = "hey_jarvis" if word == "hey_auri" else "hey_auri"  # the other wake word is a negative too
    for _name, (lang, path) in list(VOICES.items())[:3]:
        if path.is_file():
            neg_parts.append(augment(synth(path, POSITIVE[other][lang][0], 1.0), "clean", rng))
    for extra in build.extra_negatives:  # e.g. real speech over music (--negative-wav)
        neg_parts.append(read_wav(extra))
    if user_dir:
        mine = [(f"user|{p.name}", augment(read_wav(p), "clean", rng)) for p in sorted((user_dir / word).glob("*.wav"))]
        pos = mine if build.user_only else pos + mine  # --user-only: the real gate, your voice only
        neg_parts += [read_wav(p) for p in sorted((user_dir / "negative").glob("*.wav"))]
    return pos, np.concatenate(neg_parts)


def run_stream(engine, audio: np.ndarray) -> tuple[int, float]:
    """Feed audio frame by frame; return (#detections with 1.5 s refractory, ms CPU per frame)."""
    hits, last, t, n = 0, -1e9, time.perf_counter(), 0
    for i in range(0, len(audio) - FRAME + 1, FRAME):
        n += 1
        if engine.feed(audio[i:i + FRAME]) is not None and (i - last) > 1.5 * SR:
            hits, last = hits + 1, i
    return hits, (time.perf_counter() - t) * 1000 / max(1, n)


def engines_for(word: str):
    import yaml

    from auri_jarvis.stt.engines import ParakeetStt
    from auri_jarvis.wake.engines import KwsWake, OwwWake, SttWake

    cfg = yaml.safe_load((ROOT / "config/audio.yaml").read_text("utf-8"))["wake"]
    kws_cfg = cfg["kws"]
    out = {}
    for thr in (0.15, 0.25, 0.35):
        out[f"kws@{thr}"] = lambda thr=thr: KwsWake(
            resolve(kws_cfg["model_dir"]), kws_cfg["keywords"][word],
            VOICE_DATA / f"bench_kws_{word}_{thr}.txt", threshold=thr, label=word.upper())
    if word == "hey_jarvis":
        o = cfg["oww"]
        out["oww"] = lambda: OwwWake(resolve(o["models"]["hey_jarvis"]), resolve(o["melspec"]),
                                     resolve(o["embedding"]), threshold=float(o["threshold"]))
    else:
        stt = ParakeetStt()
        out["stt_wake"] = lambda: SttWake(stt)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", choices=["hey_auri", "hey_jarvis", "both"], default="both")
    ap.add_argument("--user-dir", type=str, default="")
    ap.add_argument("--user-only", action="store_true", help="positives = only your recordings (the real gate)")
    ap.add_argument("--negative-wav", action="append", default=[], help="extra 16 kHz mono negative audio")
    ap.add_argument("--only", action="append", default=[], help="run only these engines (e.g. stt_wake)")
    args = ap.parse_args()
    build.extra_negatives = [Path(p) for p in args.negative_wav]
    build.user_only = args.user_only
    rng = np.random.default_rng(7)
    words = ["hey_auri", "hey_jarvis"] if args.word == "both" else [args.word]
    for word in words:
        pos, neg = build(word, resolve(args.user_dir) if args.user_dir else None, rng)
        neg_h = len(neg) / SR / 3600
        print(f"\n=== {word}: {len(pos)} positives, negatives {len(neg) / SR / 60:.1f} min ===")
        for name, make in engines_for(word).items():
            if args.only and name not in args.only:
                continue
            eng = make()
            found, misses, costs = 0, [], []
            for label, audio in pos:
                eng.reset()
                hits, ms = run_stream(eng, audio)
                costs.append(ms)
                found += hits > 0
                if hits == 0:
                    misses.append(label)
            eng.reset()
            fa, ms_neg = run_stream(eng, neg)
            print(f"{name:10s} recall {found / len(pos):6.1%}  false/h {fa / neg_h:6.1f} ({fa} in "
                  f"{neg_h * 60:.1f} min)  cpu {np.median([*costs, ms_neg]):5.2f} ms/frame")
            by_kind = {k: sum(1 for m in misses if f"|{k}|" in m) for k in ("clean", "noisy", "far")}
            if misses:
                print(f"           misses by condition: {by_kind}; e.g. {misses[:3]}")


if __name__ == "__main__":
    main()
