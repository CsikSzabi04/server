"""Pre-render Auri's fixed phrases (acks + onboarding voice samples) into the TTS cache.

    python scripts/prerender_phrases.py              # silent; premium phrases cost credits ONCE
    python scripts/prerender_phrases.py --dry-run    # only show what would be rendered

Signature phrases are stored on disk (data/voice/tts_cache), so later plays are instant and
free. Uses config/audio.yaml + .env exactly like the daemon (premium only with a key and
within the monthly budget; otherwise local Piper).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml
from dotenv import dotenv_values

from auri_jarvis.audio._paths import ROOT
from auri_jarvis.tts.mouth import ACKS, SAMPLE_TEXT, AuriMouth


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config/audio.yaml").read_text("utf-8"))
    cfg["env"] = dict(dotenv_values(ROOT / ".env"))
    jobs = [(cfg["tts"].get("default_voice", "daniel"), a) for a in ACKS]
    jobs += [(voice, text) for voice, text in SAMPLE_TEXT.items()]
    if args.dry_run:
        for voice, text in jobs:
            print(f"{voice:7s} {text}")
        return
    mouth = AuriMouth(cfg, None, output=lambda block: None)  # silent: nothing is played
    before = mouth._ledger.used
    for voice, text in jobs:
        mouth._voice = voice
        mouth._render(text, signature=True)
        print(f"{voice:7s} {mouth.last_engine:18s} {text}")
    print(f"\ncredits this month: {before} → {mouth._ledger.used} (budget {mouth._ledger.budget})")


if __name__ == "__main__":
    main()
