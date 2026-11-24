"""Build AuriSetup.exe — the public "Auri" desktop installer (owner: AI-3).

    .venv\\Scripts\\python installer\\build_installer.py            # uses the existing web/dist
    .venv\\Scripts\\python installer\\build_installer.py --web      # npm run build first

Output: installer/dist/  AuriSetup.exe · SHA256SUMS.txt · RELEASE_NOTES.md
Upload the exe to a GitHub Release (tag auri-v<version>, marked "latest") — the AuriGPT web
"⬇ AURI" button links to …/releases/latest/download/AuriSetup.exe.

What goes into the setup (and what never does):
  payload.zip  auri-jarvis code (auri_jarvis/, config/ — NOT me.md, scripts/, skills/,
               requirements.txt, pyproject.toml, README.md, .env.example) + web/dist
               NEVER: .env, data/, .venv/, models/, tests/, prompts/, __pycache__
  models-small.zip  the wake-word models audio.yaml references (openWakeWord ONNX, sherpa KWS);
               Piper voices are NOT bundled: the setup downloads them from Hugging Face and
               checks the sha256 recorded here (verified against the local copies at build time)
  env.defaults the PUBLIC Supabase URL + publishable/anon key (the same values the public web
               bundle ships) — refused if the key is a secret/service key
  uv.exe       pinned uv release (sha256 printed)
Safety gate: every payload file is scanned for the values of the secret keys found in
auri-jarvis/.env and web/.env*.local — the build aborts if any of them appears.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # auri-jarvis
REPO = ROOT.parent  # D:\Projectss\Server
WEB = REPO / "web"
BUILD = HERE / "build"
RES = BUILD / "res"
DIST = HERE / "dist"
UV_VERSION = "0.13.9"
UV_URL = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
UA = {"User-Agent": "AuriBuild"}

sys.path.insert(0, str(ROOT))

INCLUDE_DIRS = ["auri_jarvis", "config", "scripts", "skills"]
INCLUDE_FILES = ["requirements.txt", "pyproject.toml", "README.md", ".env.example", "ruff.toml"]
EXCLUDE_PARTS = {"__pycache__", ".venv", "data", "models", "tests", "prompts", ".cache", ".pytest_cache", ".ruff_cache"}
EXCLUDE_NAMES = {".env", "me.md"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".wav", ".mp3"}
SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD)", re.I)


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            v = v.split(" #", 1)[0].strip().strip('"').strip("'")
            out[k.strip()] = v
    return out


def secret_values() -> list[str]:
    """Values of secret-looking keys in the local env files (never printed). The public
    Supabase key is allowed (it ships in the public web bundle anyway)."""
    vals: list[str] = []
    for f in [ROOT / ".env", *WEB.glob(".env*.local")]:
        for k, v in read_env(f).items():
            if SECRET_NAME.search(k) and "SUPABASE_ANON_KEY" not in k and len(v) >= 8:
                vals.append(v)
    return vals


def keep(rel: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return False
    return rel.name not in EXCLUDE_NAMES and rel.suffix.lower() not in EXCLUDE_SUFFIXES


def build_payload(out: Path, *, root: Path = ROOT, web_dist: Path = WEB / "dist") -> list[str]:
    """payload.zip: auri-jarvis/<code> + web/dist/<build>. Returns the archived names."""
    names: list[str] = []
    if not (web_dist / "index.html").is_file():
        raise SystemExit(f"Nincs web build: {web_dist} — futtasd: --web (vagy cd web; npm run build)")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for d in INCLUDE_DIRS:
            base = root / d
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("*")):
                rel = p.relative_to(root)
                if p.is_file() and keep(rel):
                    name = f"auri-jarvis/{rel.as_posix()}"
                    z.write(p, name)
                    names.append(name)
        for f in INCLUDE_FILES:
            p = root / f
            if p.is_file():
                z.write(p, f"auri-jarvis/{f}")
                names.append(f"auri-jarvis/{f}")
        for p in sorted(web_dist.rglob("*")):
            if p.is_file():
                name = f"web/dist/{p.relative_to(web_dist).as_posix()}"
                z.write(p, name)
                names.append(name)
    return names


def scan_for_secrets(zip_path: Path, secrets: list[str]) -> list[str]:
    hits: list[str] = []
    needles = [s.encode() for s in secrets if s]
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            data = z.read(info)
            if any(n in data for n in needles):
                hits.append(info.filename)
    return hits


def env_defaults() -> str:
    """Public Supabase values for the desktop .env (refuses a secret/service key)."""
    env = read_env(WEB / ".env.local")
    url, key = env.get("VITE_SUPABASE_URL", ""), env.get("VITE_SUPABASE_ANON_KEY", "")
    if not url or not key:
        log("  ! web/.env.local: nincs VITE_SUPABASE_* → a desktop app csak vendég módban indul")
        return ""
    if key.startswith("sb_secret_"):
        raise SystemExit("ELUTASÍTVA: a VITE_SUPABASE_ANON_KEY egy titkos kulcs!")
    if key.count(".") == 2:
        payload = key.split(".")[1] + "=" * (-len(key.split(".")[1]) % 4)
        if json.loads(base64.urlsafe_b64decode(payload)).get("role") != "anon":
            raise SystemExit("ELUTASÍTVA: a Supabase JWT nem 'anon' szerepkörű!")
    elif not key.startswith("sb_publishable_"):
        raise SystemExit("ELUTASÍTVA: ismeretlen Supabase-kulcsformátum")
    return f"SUPABASE_URL={url.rstrip('/')}\nSUPABASE_ANON_KEY={key}\n"


def models_small(out: Path) -> list[str]:
    """Wake-word models referenced by config/audio.yaml (small, redistributable with notice)."""
    import yaml

    audio = yaml.safe_load((ROOT / "config" / "audio.yaml").read_text(encoding="utf-8")) or {}
    wake = audio.get("wake", {})
    files: list[Path] = []
    oww = wake.get("oww", {}) or {}
    for key in ("melspec", "embedding"):
        if oww.get(key):
            files.append(ROOT / oww[key])
    for p in (oww.get("models") or {}).values():
        if p:
            files.append(ROOT / p)
    kws_dir = (wake.get("kws") or {}).get("model_dir")
    if kws_dir:
        for p in sorted((ROOT / kws_dir).glob("*")):
            if p.is_file() and (p.suffix in {".txt", ".model"} or ".int8.onnx" in p.name):
                files.append(p)
    names = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if not f.is_file():
                raise SystemExit(f"Hiányzó modell: {f}")
            rel = f.relative_to(ROOT / "models").as_posix()
            z.write(f, rel)
            names.append(rel)
        z.writestr(
            "MODELS_NOTICE.txt",
            "openWakeWord pretrained models (melspectrogram, embedding, hey_jarvis): (c) David Scripka, "
            "CC BY-NC-SA 4.0 — https://github.com/dscripka/openWakeWord\n"
            "sherpa-onnx KWS zipformer (gigaspeech 3.3M): k2-fsa, Apache-2.0 — https://github.com/k2-fsa/sherpa-onnx\n"
            "Piper voices are downloaded by the setup from https://huggingface.co/rhasspy/piper-voices "
            "(see each voice's MODEL_CARD for its license).\n",
        )
    return names


def piper_manifest() -> list[dict[str, str]]:
    import yaml

    audio = yaml.safe_load((ROOT / "config" / "audio.yaml").read_text(encoding="utf-8")) or {}
    piper = (audio.get("tts") or {}).get("piper") or {}
    out = []
    for rel in filter(None, (piper.get("voice_hu"), piper.get("voice_en"))):
        stem = Path(rel).name.removesuffix(".onnx")  # hu_HU-imre-medium
        lang_region, name, quality = stem.split("-")
        lang = lang_region.split("_")[0]
        for suffix in (".onnx", ".onnx.json"):
            local = ROOT / (rel + (".json" if suffix == ".onnx.json" else ""))
            url = f"{HF}/{lang}/{lang_region}/{name}/{quality}/{stem}{suffix}"
            want = sha256_file(local)
            if suffix == ".onnx.json":  # small → verify by downloading
                got = sha256_bytes(fetch(url))
            else:  # large → HF LFS metadata
                tree = json.loads(
                    fetch(
                        f"https://huggingface.co/api/models/rhasspy/piper-voices/tree/main/{lang}/{lang_region}/{name}/{quality}"
                    )
                )
                got = next(f["lfs"]["oid"] for f in tree if f["path"].endswith(stem + suffix))
            if got != want:
                raise SystemExit(f"A Hugging Face-en lévő {stem}{suffix} eltér a helyitől — nem építek rá.")
            out.append({"url": url, "path": f"models/piper/{stem}{suffix}", "sha256": want})
            log(f"  ✓ {stem}{suffix} (HF = helyi)")
    return out


def get_uv(dest: Path) -> str:
    cache = BUILD / f"uv-{UV_VERSION}.zip"
    if not cache.is_file():
        log(f"  uv {UV_VERSION} letöltése…")
        cache.write_bytes(fetch(UV_URL))
    digest = sha256_file(cache)
    with zipfile.ZipFile(cache) as z:
        member = next(n for n in z.namelist() if n.endswith("uv.exe"))
        dest.write_bytes(z.read(member))
    return digest


def make_icon(dest: Path) -> None:
    from auri_jarvis.tray import COLORS
    from auri_jarvis.tray import make_icon as mk

    imgs = [mk(COLORS["idle"], s) for s in (256, 64, 48, 32, 16)]
    imgs[0].save(dest, format="ICO", sizes=[(s, s) for s in (256, 64, 48, 32, 16)])


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if s is not None:
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", action="store_true", help="npm run build in ../web first")
    ap.add_argument("--no-exe", action="store_true", help="prepare resources only (no PyInstaller)")
    args = ap.parse_args()

    from auri_jarvis import __version__
    from auri_jarvis.config import load_config

    version = __version__
    tag = f"auri-v{version}"
    log(f"== Auri setup {version} ({tag})")
    shutil.rmtree(RES, ignore_errors=True)
    RES.mkdir(parents=True)
    DIST.mkdir(exist_ok=True)

    if args.web:
        log("-- web build")
        subprocess.run("npm run build", cwd=WEB, shell=True, check=True)

    log("-- payload.zip")
    names = build_payload(RES / "payload.zip")
    bad = [n for n in names if Path(n).name in EXCLUDE_NAMES or "/data/" in n or "/.venv/" in n]
    if bad:
        raise SystemExit(f"Tiltott fájl a csomagban: {bad[:5]}")
    hits = scan_for_secrets(RES / "payload.zip", secret_values())
    if hits:
        raise SystemExit(f"TITOK a csomagban — leállok: {hits[:5]}")
    log(f"  {len(names)} fájl, {(RES / 'payload.zip').stat().st_size / 2**20:.1f} MB, titok-ellenőrzés: tiszta")

    log("-- env.defaults (publikus Supabase-értékek)")
    (RES / "env.defaults").write_text(env_defaults(), encoding="utf-8")

    log("-- models-small.zip")
    small = models_small(RES / "models-small.zip")
    log(f"  {len(small)} fájl, {(RES / 'models-small.zip').stat().st_size / 2**20:.1f} MB")

    log("-- Piper-hangok (Hugging Face, sha256)")
    piper = piper_manifest()

    log("-- uv.exe")
    uv_sha = get_uv(RES / "uv.exe")
    log(f"  uv {UV_VERSION} zip sha256 {uv_sha}")

    log("-- ikon")
    make_icon(RES / "auri.ico")

    cfg = load_config(environ={})
    manifest = {
        "version": version,
        "tag": tag,
        "piper": piper,
        "ollama_models": [m for m in (cfg.get("llm", {}).get("model"), cfg.get("llm", {}).get("embed_model")) if m],
        "stt": {
            "model": cfg.get("stt", {}).get("parakeet_model", "nemo-parakeet-tdt-0.6b-v3"),
            "quantization": cfg.get("stt", {}).get("parakeet_quantization", "int8"),
        },
        "uv": {"version": UV_VERSION, "zip_sha256": uv_sha},
    }
    (RES / "build_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log(f"  Ollama-modellek: {', '.join(manifest['ollama_models'])}")

    if args.no_exe:
        log("== erőforrások kész (--no-exe)")
        return 0

    log("-- PyInstaller")
    sep = ";"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "AuriSetup",
        "--icon",
        str(RES / "auri.ico"),
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD / "pyi"),
        "--specpath",
        str(BUILD),
    ]
    for f in ("payload.zip", "models-small.zip", "uv.exe", "auri.ico", "build_manifest.json", "env.defaults"):
        cmd += ["--add-data", f"{RES / f}{sep}."]
    cmd.append(str(HERE / "setup_app.py"))
    subprocess.run(cmd, check=True)

    exe = DIST / "AuriSetup.exe"
    digest = sha256_file(exe)
    (DIST / "SHA256SUMS.txt").write_text(f"{digest}  AuriSetup.exe\n", encoding="utf-8")
    (DIST / "RELEASE_NOTES.md").write_text(
        f"# Auri {version} — asztali app\n\n"
        "Helyi, ingyenes hangasszisztens Windowsra — „Hey Auri”, helyi nyelvi modell (Ollama), "
        "AuriGPT-kinézet, ARCHIVE és BRAIN.\n\n"
        "**Telepítés:** töltsd le az `AuriSetup.exe`-t és futtasd (rendszergazdai jog nem kell). "
        "A telepítő letölti a futtatókörnyezetet, a hangmodelleket és — ha kéred — az Ollamát és a nyelvi modellt.\n\n"
        "A Windows SmartScreen figyelmeztethet (nincs kódaláírás): *További információ → Futtatás mindenképp*.\n\n"
        f"SHA256 (`AuriSetup.exe`): `{digest}`\n",
        encoding="utf-8",
    )
    log(f"== {exe}  {exe.stat().st_size / 2**20:.1f} MB  sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
