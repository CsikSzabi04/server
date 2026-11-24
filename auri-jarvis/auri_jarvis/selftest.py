"""auri_jarvis.selftest — `python -m auri_jarvis --selftest` (owner: AI-3).

Checks the environment without side effects and without spending credits:
config files · AI-1/AI-2 factories · Ollama + configured models · microphone · Piper voices ·
STT model cache · key *presence* (never values, never validity) · HUD port · data dir · web build.
Exit code 0 = no FAIL (warnings allowed), 1 = at least one FAIL.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import get

OK, WARN, FAIL = "ok", "warn", "fail"
_SYM = {OK: "✓", WARN: "!", FAIL: "✗"}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def _root(cfg: dict[str, Any]) -> Path:
    return Path(cfg["paths"]["root"])


def check_config(cfg: dict[str, Any]) -> list[Check]:
    p = cfg["paths"]
    out = [Check("konfig", OK, "betöltve: " + ", ".join(p["loaded"]))]
    for m in p["missing"]:
        owner = {"audio.yaml": "AI-1", "mind.yaml": "AI-2"}.get(m, "?")
        out.append(Check(f"konfig {m}", WARN, f"még nincs ({owner} zónája)"))
    return out


def check_factories(cfg: dict[str, Any]) -> list[Check]:
    from .__main__ import FACTORIES

    out = []
    for kind, (module, name, owner) in FACTORIES.items():
        spec = importlib.util.find_spec(module)
        if spec is None:
            out.append(Check(f"gyár {kind}", WARN, f"{module} még nincs ({owner}) — --text módban fake/Echo"))
            continue
        try:
            mod = importlib.import_module(module)
        except Exception as e:
            out.append(Check(f"gyár {kind}", FAIL, f"{module} importhiba: {type(e).__name__}: {e}"))
            continue
        ok = callable(getattr(mod, name, None))
        out.append(Check(f"gyár {kind}", OK if ok else FAIL, f"{module}.{name}" + ("" if ok else " hiányzik")))
    return out


def _user_env(name: str) -> str | None:
    """Persistent per-user env var (HKCU\\Environment) on Windows; None elsewhere / unset."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, name)
            return str(val) or None
    except (ImportError, OSError):
        return None


def check_ollama(cfg: dict[str, Any]) -> list[Check]:
    base = str(get(cfg, "llm.base_url", "http://127.0.0.1:11434")).rstrip("/")
    out: list[Check] = []
    user_om = _user_env("OLLAMA_MODELS")  # the persistent value (what a fresh Ollama sees)
    om = user_om or os.environ.get("OLLAMA_MODELS")
    if om and not Path(om).is_dir():
        out.append(Check("OLLAMA_MODELS", WARN, f"nem létező mappára mutat: {om}"))
    elif user_om and os.environ.get("OLLAMA_MODELS") not in (None, user_om):
        out.append(Check("OLLAMA_MODELS", OK, f"{user_om} (ez a folyamat még a régi értéket látja — új terminál kell)"))
    try:
        r = httpx.get(f"{base}/api/tags", timeout=3.0)
        r.raise_for_status()
        names = {m.get("name", "") for m in r.json().get("models", [])}
    except Exception as e:
        out.append(Check("Ollama", FAIL, f"nem érhető el ({base}): {type(e).__name__} — telepítés: spec 10. fejezet"))
        return out
    out.append(Check("Ollama", OK, f"{base} · {len(names)} modell"))
    wanted = [get(cfg, "llm.model"), get(cfg, "llm.embed_model")]
    if not any(wanted):
        wanted = ["qwen3.5:4b", "embeddinggemma"]
        out.append(Check("LLM-modellek", WARN, "a mind.yaml még nem nevez meg modellt — a spec alapértékeit nézem"))
    for w in filter(None, wanted):
        have = w in names or f"{w}:latest" in names
        out.append(Check(f"modell {w}", OK if have else FAIL, "megvan" if have else f"hiányzik → ollama pull {w}"))
    return out


def check_microphone(cfg: dict[str, Any]) -> list[Check]:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
        default = sd.query_devices(kind="input")
    except Exception as e:
        return [Check("mikrofon", FAIL, f"nincs bemeneti eszköz: {type(e).__name__}: {e}")]
    want = cfg["env"].get("JARVIS_INPUT_DEVICE") or get(cfg, "audio.input_device", "auto")
    return [
        Check(
            "mikrofon",
            OK if inputs else FAIL,
            f"alapértelmezett: {default.get('name')} · {len(inputs)} bemenet · választás: {want}",
        )
    ]


def check_piper(cfg: dict[str, Any]) -> list[Check]:
    root = _root(cfg)
    paths = [get(cfg, "tts.piper.voice_hu"), get(cfg, "tts.piper.voice_en")]
    if not any(paths):
        found = sorted((root / "models" / "piper").glob("*.onnx")) if (root / "models" / "piper").is_dir() else []
        if found:
            return [Check("Piper-hangok", OK, ", ".join(p.name for p in found))]
        return [Check("Piper-hangok", WARN, "nincs még letöltve (models/piper) — AI-1 / spec 10.6")]
    out = []
    for p in filter(None, paths):
        full = (root / p) if not Path(p).is_absolute() else Path(p)
        out.append(Check(f"Piper {Path(p).name}", OK if full.is_file() else WARN, "megvan" if full.is_file() else "hiányzik"))
    return out


def check_stt(cfg: dict[str, Any]) -> list[Check]:
    hub = Path(os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    if hub.name != "hub":
        hub = hub / "hub"
    roots = [hub, _root(cfg) / "models"]
    hits: list[str] = []
    for r in roots:
        if r.is_dir():
            hits += [p.name for p in r.iterdir() if "parakeet" in p.name.lower()]
    if hits:
        return [Check("STT-modell (Parakeet)", OK, ", ".join(sorted(set(hits))[:3]))]
    return [Check("STT-modell (Parakeet)", WARN, "nincs a cache-ben — az első futás tölti le (AI-1)")]


def check_keys(cfg: dict[str, Any]) -> list[Check]:
    env = cfg["env"]
    out = []
    for key, why in (
        ("ELEVENLABS_API_KEY", "nélküle csak Piper szól"),
        ("SUPABASE_URL", "nélküle nincs bejelentkezés (csak vendég mód)"),
        ("SUPABASE_ANON_KEY", "nélküle nincs bejelentkezés (csak vendég mód)"),
    ):
        present = bool(env.get(key))
        out.append(Check(key, OK if present else WARN, "beállítva" if present else f"hiányzik — {why}"))
    return out


def check_port(cfg: dict[str, Any]) -> list[Check]:
    host = str(get(cfg, "hud.host", "127.0.0.1"))
    port = int(get(cfg, "hud.port", 8790))
    if host not in ("127.0.0.1", "localhost", "::1"):
        return [Check("HUD-port", FAIL, f"a hud.host csak 127.0.0.1 lehet (most: {host})")]
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return [Check("HUD-port", FAIL, f"{host}:{port} foglalt (fut már a daemon?)")]
    return [Check("HUD-port", OK, f"{host}:{port} szabad")]


def check_data(cfg: dict[str, Any]) -> list[Check]:
    d = Path(cfg["paths"]["data_dir"]) / "body"
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return [Check("adatmappa", FAIL, f"{d} nem írható: {e}")]
    return [Check("adatmappa", OK, str(d))]


def check_web(cfg: dict[str, Any]) -> list[Check]:
    dist = (_root(cfg) / str(get(cfg, "hud.web_dist", "../web/dist"))).resolve()
    out = [
        Check(
            "HUD web build",
            OK if (dist / "index.html").is_file() else WARN,
            str(dist) if (dist / "index.html").is_file() else f"nincs build ({dist}) → cd web; npm run build",
        )
    ]
    chrome = get(cfg, "hud.chrome_path")
    if chrome:
        out.append(Check("Chrome", OK if Path(chrome).is_file() else WARN, chrome))
    return out


CHECKS: list[Callable[[dict[str, Any]], list[Check]]] = [
    check_config,
    check_factories,
    check_ollama,
    check_microphone,
    check_piper,
    check_stt,
    check_keys,
    check_port,
    check_data,
    check_web,
]


def collect(cfg: dict[str, Any]) -> list[Check]:
    results: list[Check] = []
    for fn in CHECKS:
        try:
            results += fn(cfg)
        except Exception as e:
            results.append(Check(fn.__name__, FAIL, f"{type(e).__name__}: {e}"))
    return results


def run_selftest(cfg: dict[str, Any]) -> int:
    results = collect(cfg)
    print("Auri J.A.R.V.I.S. — önellenőrzés")
    for c in results:
        print(f"  {_SYM[c.status]} {c.name}: {c.detail}")
    fails = sum(c.status == FAIL for c in results)
    warns = sum(c.status == WARN for c in results)
    print(f"Eredmény: {'HIBA' if fails else 'OK'} — {fails} hiba, {warns} figyelmeztetés")
    with contextlib.suppress(Exception):
        import sys

        sys.stdout.flush()
    return 1 if fails else 0
