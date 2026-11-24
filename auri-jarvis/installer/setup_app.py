"""Auri — Windows setup wizard (owner: AI-3). Public name "Auri" (spec §8: the J.A.R.V.I.S.
name stays private). Built into AuriSetup.exe by
installer/build_installer.py (PyInstaller, one file, windowed).

Per-user install, no admin rights:  %LOCALAPPDATA%\\Programs\\Auri
  app\\auri-jarvis\\   the daemon (same code as in the repo) + models\\ + .venv\\ + data\\ (runtime)
  app\\web\\dist\\     the HUD / AuriGPT web build the daemon serves
  tools\\uv.exe        bundled uv (Python + packages)      python\\  uv-managed CPython 3.12
  AuriSetup.exe        a copy of this setup → "Apps & features" uninstall / repair

Steps: unpack · Python 3.12 + pinned packages (uv) · voice models (Piper from Hugging Face,
sha256-verified; small wake-word models bundled) · speech-recognition model (optional) ·
Ollama + the LLM (optional) · shortcuts · start at login (optional) · uninstall entry.

CLI (also for automated tests):
  AuriSetup.exe [--silent] [--dir D] [--no-start-menu] [--no-desktop] [--autostart]
                      [--no-ollama] [--no-stt] [--launch]
  AuriSetup.exe --uninstall [--dir D] [--silent] [--purge]
Updating = running a newer setup over an existing install (.env, config/me.md and data/ are kept).
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_ID = "Auri"
APP_NAME = "Auri"
TASK_NAME = "Auri JARVIS"  # = scripts/install_autostart.ps1 (internal name, kept)
UA = "AuriSetup"
CREATE_NO_WINDOW = 0x08000000
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"


def resource(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent / "build" / "res"))
    return base / name


def load_manifest() -> dict[str, Any]:
    try:
        return json.loads(resource("build_manifest.json").read_text(encoding="utf-8"))
    except OSError:
        return {"version": "dev", "tag": "dev", "piper": [], "ollama_models": [], "stt": {}}


MANIFEST = load_manifest()
VERSION = str(MANIFEST.get("version", "dev"))


def default_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / APP_ID


@dataclass
class Options:
    install_dir: Path
    start_menu: bool = True
    desktop: bool = True
    autostart: bool = False  # opt-in (the user decided: no autostart by default)
    ollama: bool = True
    stt: bool = True
    launch: bool = True


class InstallError(RuntimeError):
    pass


# ── helpers ──────────────────────────────────────────────────────────────────
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, *, sha256: str | None, on_progress: Callable[[int, int], None]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and sha256 and sha256_of(dest) == sha256:
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, tmp.open("wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 18):
            f.write(chunk)
            done += len(chunk)
            on_progress(done, total)
    if sha256 and sha256_of(tmp) != sha256:
        tmp.unlink(missing_ok=True)
        raise InstallError(f"Sérült letöltés (sha256 eltér): {url}")
    tmp.replace(dest)


def free_gb(path: Path) -> float:
    p = path
    while not p.exists() and p.parent != p:
        p = p.parent
    return shutil.disk_usage(p).free / 2**30


def ollama_exe() -> Path | None:
    found = shutil.which("ollama")
    if found:
        return Path(found)
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return cand if cand.is_file() else None


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def ollama_models() -> set[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            return {m.get("name", "") for m in json.load(r).get("models", [])}
    except (OSError, ValueError):
        return set()


def powershell(script: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
        creationflags=CREATE_NO_WINDOW,
        env={**os.environ, **(env or {})},
        capture_output=True,
    )


def start_menu_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def desktop_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


# ── the installer ────────────────────────────────────────────────────────────
class Installer:
    def __init__(self, opts: Options, log: Callable[[str], None], progress: Callable[[float, str], None]) -> None:
        self.o = opts
        self.log = log
        self.progress = progress
        self.dir = opts.install_dir
        self.app = self.dir / "app" / "auri-jarvis"
        self.venv = self.app / ".venv"
        self.uv = self.dir / "tools" / "uv.exe"
        self.env = {
            **os.environ,
            "UV_PYTHON_INSTALL_DIR": str(self.dir / "python"),
            "UV_CACHE_DIR": os.environ.get("AURI_UV_CACHE") or str(self.dir / "cache"),
            "UV_NO_PROGRESS": "1",
            "PYTHONUTF8": "1",
        }
        self._file_log = None
        self._sub: tuple[float, float] = (0.0, 1.0)

    # steps: (weight, title, fn)
    def steps(self) -> list[tuple[float, str, Callable[[], None]]]:
        s: list[tuple[float, str, Callable[[], None]]] = [
            (3, "Fájlok kicsomagolása", self.unpack),
            (2, "Python 3.12 (uv)", self.python),
            (35, "Csomagok telepítése (~700 MB letöltés)", self.packages),
            (8, "Hangmodellek (Piper)", self.voices),
        ]
        if self.o.stt:
            s.append((12, "Beszédfelismerő modell (Parakeet, ~650 MB)", self.stt_model))
        if self.o.ollama:
            s.append((35, "Ollama + nyelvi modell", self.ollama))
        s += [
            (1, "Parancsikonok", self.shortcuts),
            (1, "Indítás bejelentkezéskor", self.autostart),
            (1, "Eltávolító bejegyzése", self.register),
        ]
        return s

    def run(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._file_log = (self.dir / "install.log").open("a", encoding="utf-8")
        self.say(f"== {APP_NAME} {VERSION} telepítése: {self.dir}  ({time.strftime('%Y-%m-%d %H:%M:%S')})")
        need = 8 if self.o.ollama else 3
        if free_gb(self.dir) < need:
            raise InstallError(f"Kevés a szabad hely: legalább {need} GB kell ({free_gb(self.dir):.1f} GB szabad).")
        steps = self.steps()
        total = sum(w for w, _, _ in steps)
        done = 0.0
        for w, title, fn in steps:
            self.progress(done / total, title)
            self.say(f"-- {title}")
            self._sub = (done / total, w / total)
            fn()
            done += w
        self.progress(1.0, "Kész")
        self.say("== Kész.")

    def say(self, line: str) -> None:
        self.log(line)
        if self._file_log is not None:
            self._file_log.write(line + "\n")
            self._file_log.flush()

    def sub(self, frac: float, title: str) -> None:
        base, width = self._sub
        self.progress(base + width * max(0.0, min(1.0, frac)), title)

    def exec(self, args: list[str], *, cwd: Path | None = None, title: str = "") -> None:
        self.say("   $ " + " ".join(Path(a).name if i == 0 else a for i, a in enumerate(args)))
        p = subprocess.Popen(
            args,
            cwd=str(cwd) if cwd else None,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        assert p.stdout is not None
        n = 0
        for line in p.stdout:
            line = line.rstrip()
            if line:
                n += 1
                self.say("     " + line[:300])
                if title:
                    self.sub(min(0.95, n / 120), title)
        if p.wait() != 0:
            raise InstallError(
                f"Sikertelen lépés: {Path(args[0]).name} {' '.join(args[1:3])} (kód {p.returncode}) — részletek: install.log"
            )

    # 1 ─ unpack ──────────────────────────────────────────────────────────────
    def unpack(self) -> None:
        root = self.dir / "app"
        for stale in (self.app / "auri_jarvis", root / "web" / "dist"):  # code is replaced on update
            shutil.rmtree(stale, ignore_errors=True)
        with zipfile.ZipFile(resource("payload.zip")) as z:
            z.extractall(root)
        with zipfile.ZipFile(resource("models-small.zip")) as z:
            z.extractall(self.app / "models")
        self.uv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resource("uv.exe"), self.uv)
        env_file = self.app / ".env"
        if not env_file.exists():  # never overwrite the user's own keys on update
            defaults = resource("env.defaults")
            text = (self.app / ".env.example").read_text(encoding="utf-8")
            if defaults.is_file():
                for line in defaults.read_text(encoding="utf-8").splitlines():
                    k, _, v = line.partition("=")
                    text = "\n".join(f"{k}={v}" if ln.split("=", 1)[0].strip() == k else ln for ln in text.splitlines()) + "\n"
            env_file.write_text(text, encoding="utf-8")
            self.say("   .env létrehozva (ElevenLabs-kulcs nélkül → helyi Piper-hang; később megadható)")

    # 2 ─ python + packages ───────────────────────────────────────────────────
    def python(self) -> None:
        self.exec([str(self.uv), "python", "install", "3.12"])
        args = [str(self.uv), "venv", "--python", "3.12", str(self.venv)]
        if self.venv.exists():
            args.insert(2, "--allow-existing")
        self.exec(args)

    def packages(self) -> None:
        py = self.venv / "Scripts" / "python.exe"
        self.exec(
            [str(self.uv), "pip", "install", "--python", str(py), "-r", str(self.app / "requirements.txt")],
            title="Csomagok telepítése",
        )

    # 3 ─ models ──────────────────────────────────────────────────────────────
    def voices(self) -> None:
        items = MANIFEST.get("piper", [])
        for i, it in enumerate(items):
            dest = self.app / it["path"]
            name = Path(it["path"]).name

            def prog(done: int, total: int, i: int = i, name: str = name) -> None:
                frac = (i + (done / total if total else 0)) / max(1, len(items))
                self.sub(frac, f"Hangmodell: {name}")

            download(it["url"], dest, sha256=it["sha256"], on_progress=prog)
            self.say(f"   ✓ {name}")

    def stt_model(self) -> None:
        stt = MANIFEST.get("stt", {})
        name, quant = stt.get("model", "nemo-parakeet-tdt-0.6b-v3"), stt.get("quantization", "int8")
        py = self.venv / "Scripts" / "python.exe"
        code = f"import onnx_asr; onnx_asr.load_model({name!r}, quantization={quant!r}); print('ok')"
        self.exec([str(py), "-c", code], title="Beszédfelismerő modell")

    # 4 ─ ollama ──────────────────────────────────────────────────────────────
    def ollama(self) -> None:
        exe = ollama_exe()
        if exe is None:
            setup = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
            self.say("   Ollama nincs telepítve → letöltés (ollama.com)…")
            download(
                "https://ollama.com/download/OllamaSetup.exe",
                setup,
                sha256=None,
                on_progress=lambda d, t: self.sub(0.3 * (d / t if t else 0), "Ollama letöltése"),
            )
            self.exec([str(setup), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"])
            exe = ollama_exe()
            if exe is None:
                raise InstallError("Az Ollama telepítése nem sikerült — telepítsd kézzel: https://ollama.com/download")
        if not ollama_up():
            app = exe.with_name("ollama app.exe")
            target = [str(app)] if app.is_file() else [str(exe), "serve"]
            subprocess.Popen(target, creationflags=CREATE_NO_WINDOW | 0x00000008, close_fds=True)  # DETACHED
            for _ in range(60):
                if ollama_up():
                    break
                time.sleep(1)
            else:
                raise InstallError("Az Ollama nem indult el (127.0.0.1:11434).")
        have = ollama_models()
        models = [m for m in MANIFEST.get("ollama_models", []) if m and m not in have and f"{m}:latest" not in have]
        for i, m in enumerate(models):
            self.pull(m, i, len(models))
        self.say("   ✓ Ollama kész: " + ", ".join(MANIFEST.get("ollama_models", [])))

    def pull(self, model: str, i: int, n: int) -> None:
        self.say(f"   ollama pull {model}")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/pull",
            data=json.dumps({"model": model, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        last = 0.0
        with urllib.request.urlopen(req, timeout=3600) as r:
            for raw in r:
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                if ev.get("error"):
                    raise InstallError(f"ollama pull {model}: {ev['error']}")
                total, comp = ev.get("total") or 0, ev.get("completed") or 0
                frac = 0.3 + 0.7 * ((i + (comp / total if total else 0)) / max(1, n))
                if time.monotonic() - last > 0.5:
                    last = time.monotonic()
                    pct = f" {comp * 100 // total}%" if total else ""
                    self.sub(frac, f"Modell: {model}{pct}")
        self.say(f"   ✓ {model}")

    # 5 ─ shortcuts, autostart, uninstall entry ──────────────────────────────
    def shortcut(self, lnk: Path) -> None:
        lnk.parent.mkdir(parents=True, exist_ok=True)
        powershell(
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:AJ_LNK);"
            "$s.TargetPath=$env:AJ_TARGET;$s.Arguments='-m auri_jarvis';$s.WorkingDirectory=$env:AJ_CWD;"
            "$s.IconLocation=$env:AJ_ICON;$s.Description='Auri — helyi hangasszisztens';$s.Save()",
            env={
                "AJ_LNK": str(lnk),
                "AJ_TARGET": str(self.venv / "Scripts" / "pythonw.exe"),
                "AJ_CWD": str(self.app),
                "AJ_ICON": str(self.dir / "auri.ico"),
            },
        )

    def shortcuts(self) -> None:
        shutil.copy2(resource("auri.ico"), self.dir / "auri.ico")
        if self.o.start_menu:
            self.shortcut(start_menu_dir() / f"{APP_NAME}.lnk")
        if self.o.desktop:
            self.shortcut(desktop_dir() / f"{APP_NAME}.lnk")

    def autostart(self) -> None:
        if not self.o.autostart:
            self.say("   (kihagyva)")
            return
        script = self.app / "scripts" / "install_autostart.ps1"
        self.exec(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Yes"])

    def register(self) -> None:
        import winreg

        me = Path(sys.executable) if getattr(sys, "frozen", False) else None
        dest = self.dir / "AuriSetup.exe"
        if me is not None and me.resolve() != dest.resolve():
            shutil.copy2(me, dest)
        size_kb = 0
        with contextlib.suppress(OSError):
            size_kb = sum(f.stat().st_size for f in self.dir.rglob("*") if f.is_file()) // 1024
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            for name, val in (
                ("DisplayName", APP_NAME),
                ("DisplayVersion", VERSION),
                ("Publisher", "Auri"),
                ("InstallLocation", str(self.dir)),
                ("DisplayIcon", str(self.dir / "auri.ico")),
                ("UninstallString", f'"{dest}" --uninstall --dir "{self.dir}"'),
                ("QuietUninstallString", f'"{dest}" --uninstall --silent --dir "{self.dir}"'),
                ("URLInfoAbout", "https://github.com/CsikSzabi04/server/releases"),
            ):
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
            for name, val in (("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", size_kb)):
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)

    def launch(self) -> None:
        subprocess.Popen(
            [str(self.venv / "Scripts" / "pythonw.exe"), "-m", "auri_jarvis"],
            cwd=str(self.app),
            creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | NEW_PROCESS_GROUP
            close_fds=True,
        )


# ── uninstall ────────────────────────────────────────────────────────────────
def uninstall(install_dir: Path, *, purge: bool, log: Callable[[str], None]) -> None:
    d = install_dir.resolve()
    log(f"Eltávolítás: {d}")
    # stop a running daemon from this install (python/pythonw under the install dir)
    with contextlib.suppress(Exception):
        powershell(
            "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and "
            "$_.ExecutablePath.StartsWith($env:AJ_DIR, [StringComparison]::OrdinalIgnoreCase) -and "
            "$_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
            env={"AJ_DIR": str(d)},
        )
    # the login task, only if it points into this install
    with contextlib.suppress(Exception):
        powershell(
            "$t=Get-ScheduledTask -TaskName $env:AJ_TASK -ErrorAction SilentlyContinue;"
            "if($t -and $t.Actions[0].Execute.StartsWith($env:AJ_DIR,[StringComparison]::OrdinalIgnoreCase)){"
            "Unregister-ScheduledTask -TaskName $env:AJ_TASK -Confirm:$false}",
            env={"AJ_TASK": TASK_NAME, "AJ_DIR": str(d)},
        )
    for lnk in (start_menu_dir() / f"{APP_NAME}.lnk", desktop_dir() / f"{APP_NAME}.lnk"):
        lnk.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        import winreg

        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    keep = set() if purge else {d / "app" / "auri-jarvis" / "data", d / "app" / "auri-jarvis" / ".env"}
    for _ in range(5):
        _remove_tree(d, keep)
        if not d.exists() or all(p in keep or any(k in p.parents for k in keep) for p in d.rglob("*")):
            break
        time.sleep(1)
    log("Kész." + ("" if purge else " (A személyes adatok — data\\ és .env — megmaradtak.)"))


def _remove_tree(root: Path, keep: set[Path]) -> None:
    if not root.exists():
        return
    for p in sorted(root.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p in keep or any(k in p.parents for k in keep) or any(p in k.parents for k in keep):
            continue
        with contextlib.suppress(OSError):
            p.rmdir() if p.is_dir() else p.unlink()
    if not keep:
        with contextlib.suppress(OSError):
            root.rmdir()


def relaunch_from_temp(argv: list[str]) -> bool:
    """A running exe can't delete itself → copy to %TEMP% and continue the uninstall from there."""
    me = Path(sys.executable)
    if not getattr(sys, "frozen", False) or "--from-temp" in argv:
        return False
    tmp = Path(tempfile.gettempdir()) / f"AuriUninstall-{os.getpid()}.exe"
    shutil.copy2(me, tmp)
    subprocess.Popen([str(tmp), *argv, "--from-temp"], close_fds=True)
    return True


def delete_self_later() -> None:
    """The %TEMP% copy of the uninstaller removes itself a moment after it exits."""
    me = Path(sys.executable)
    if not getattr(sys, "frozen", False) or "--from-temp" not in sys.argv:
        return
    with contextlib.suppress(OSError):
        subprocess.Popen(
            f'cmd /c ping -n 3 127.0.0.1 >nul & del /f /q "{me}"',
            creationflags=CREATE_NO_WINDOW | 0x00000008,  # DETACHED_PROCESS
            close_fds=True,
        )


# ── GUI ──────────────────────────────────────────────────────────────────────
ACCENT = "#1fe5ff"
BG = "#04070d"
FG = "#cfeefe"


def run_gui(opts: Options) -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    with contextlib.suppress(Exception):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    root.title(f"{APP_NAME} telepítő {VERSION}")
    root.geometry("640x520")
    root.minsize(600, 480)
    with contextlib.suppress(Exception):
        root.iconbitmap(str(resource("auri.ico")))
    style = ttk.Style(root)
    with contextlib.suppress(Exception):
        style.theme_use("vista")

    head = tk.Frame(root, bg=BG, height=84)
    head.pack(fill="x")
    tk.Label(head, text="AURI", fg=ACCENT, bg=BG, font=("Segoe UI", 22, "bold")).pack(side="left", padx=(20, 6), pady=18)
    tk.Label(head, text="// asztali hangasszisztens", fg=FG, bg=BG, font=("Segoe UI", 13)).pack(side="left", pady=24)
    tk.Label(head, text=f"v{VERSION}", fg="#5e7d8c", bg=BG, font=("Segoe UI", 9)).pack(side="right", padx=16)

    body = ttk.Frame(root, padding=18)
    body.pack(fill="both", expand=True)
    footer = ttk.Frame(root, padding=(18, 0, 18, 14))
    footer.pack(fill="x")

    def clear() -> None:
        for w in body.winfo_children():
            w.destroy()
        for w in footer.winfo_children():
            w.destroy()

    # page 1 — options
    dir_var = tk.StringVar(value=str(opts.install_dir))
    vars_ = {
        "start_menu": tk.BooleanVar(value=opts.start_menu),
        "desktop": tk.BooleanVar(value=opts.desktop),
        "autostart": tk.BooleanVar(value=opts.autostart),
        "stt": tk.BooleanVar(value=opts.stt),
        "ollama": tk.BooleanVar(value=opts.ollama),
    }

    def page_options() -> None:
        clear()
        ttk.Label(
            body,
            text="A saját gépeden futó hangasszisztens: „Hey Auri”, helyi nyelvi modell (Ollama),\n"
            "az AuriGPT kinézete, ARCHIVE és BRAIN — ugyanazzal a fiókkal.",
            justify="left",
        ).pack(anchor="w")
        box = ttk.LabelFrame(body, text="Hová?", padding=10)
        box.pack(fill="x", pady=(14, 8))
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Tallózás…", command=lambda: dir_var.set(filedialog.askdirectory() or dir_var.get())).pack(
            side="left", padx=(8, 0)
        )
        opt = ttk.LabelFrame(body, text="Beállítások", padding=10)
        opt.pack(fill="x")
        for key, label in (
            ("start_menu", "Start menü parancsikon"),
            ("desktop", "Asztali parancsikon"),
            ("autostart", "Indítás bejelentkezéskor (tálcán fut)"),
            ("stt", "Beszédfelismerő modell letöltése most (~650 MB)"),
            ("ollama", "Ollama + nyelvi modell telepítése, ha hiányzik (~3–4 GB)"),
        ):
            ttk.Checkbutton(opt, text=label, variable=vars_[key]).pack(anchor="w", pady=1)
        ttk.Label(
            body,
            text="Rendszergazdai jog nem kell. Internetkapcsolat szükséges (a csomagokat és a modelleket\n"
            "telepítéskor tölti le). Mikrofon és Windows 10/11 64 bit; 16 GB RAM ajánlott.",
            foreground="#555",
            justify="left",
        ).pack(anchor="w", pady=(10, 0))
        ttk.Button(footer, text="Mégse", command=root.destroy).pack(side="right")
        ttk.Button(footer, text="Telepítés ▶", command=page_install).pack(side="right", padx=8)

    # page 2 — progress
    q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def page_install() -> None:
        o = Options(
            install_dir=Path(dir_var.get()).expanduser(),
            **{k: v.get() for k, v in vars_.items()},
        )
        clear()
        title = ttk.Label(body, text="Előkészítés…", font=("Segoe UI", 10, "bold"))
        title.pack(anchor="w")
        bar = ttk.Progressbar(body, maximum=1000)
        bar.pack(fill="x", pady=(8, 10))
        txt = tk.Text(body, height=16, bg="#0a1220", fg=FG, insertbackground=FG, font=("Consolas", 9), wrap="none")
        txt.pack(fill="both", expand=True)
        cancel_btn = ttk.Button(footer, text="Mégse", command=root.destroy)
        cancel_btn.pack(side="right")

        def worker() -> None:
            inst = Installer(o, lambda s: q.put(("log", s)), lambda f, t: q.put(("prog", (f, t))))
            try:
                inst.run()
                q.put(("done", inst))
            except Exception as e:
                q.put(("log", traceback.format_exc()))
                if inst._file_log:
                    inst._file_log.write(traceback.format_exc())
                q.put(("fail", str(e)))

        def pump() -> None:
            try:
                while True:
                    kind, val = q.get_nowait()
                    if kind == "log":
                        txt.insert("end", val + "\n")
                        txt.see("end")
                    elif kind == "prog":
                        bar["value"] = int(val[0] * 1000)
                        title["text"] = val[1]
                    elif kind == "done":
                        page_done(val)
                        return
                    elif kind == "fail":
                        title["text"] = "Hiba történt"
                        messagebox.showerror(
                            APP_NAME, f"A telepítés megszakadt:\n\n{val}\n\nRészletek: {o.install_dir / 'install.log'}"
                        )
                        cancel_btn["text"] = "Bezárás"
                        return
            except queue.Empty:
                pass
            root.after(100, pump)

        threading.Thread(target=worker, daemon=True).start()
        pump()

    # page 3 — done
    def page_done(inst: Installer) -> None:
        clear()
        ttk.Label(body, text="✓ Az Auri telepítve.", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            body,
            text="Indítás: Start menü → Auri (vagy bejelentkezéskor, ha bekapcsoltad).\n"
            "A HUD a jobb oldali monitoron nyílik; jelentkezz be az AuriGPT-fiókoddal.\n"
            "Ébresztés: „Hey Auri”, vagy Ctrl+Alt+Space (nyomva tartva beszélj).\n\n"
            "ElevenLabs-hang (Daniel) opcionális: kulcs az app\\auri-jarvis\\.env fájlba.\n"
            "Eltávolítás: Gépház → Alkalmazások → Auri",
            justify="left",
        ).pack(anchor="w", pady=10)
        launch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Auri indítása most", variable=launch_var).pack(anchor="w")

        def finish() -> None:
            if launch_var.get():
                inst.launch()
            root.destroy()

        ttk.Button(footer, text="Befejezés", command=finish).pack(side="right")

    page_options()
    root.mainloop()
    return 0


def run_uninstall_gui(d: Path) -> int:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno(APP_NAME, f"Eltávolítod az {APP_NAME}-t?\n\n{d}"):
        return 1
    purge = messagebox.askyesno(
        APP_NAME,
        "A személyes adatokat is törölje?\n(bejelentkezési cache, naplók, hangcache, .env kulcsok)\n\n"
        "Nem = megmaradnak egy későbbi újratelepítéshez.",
    )
    lines: list[str] = []
    uninstall(d, purge=purge, log=lines.append)
    messagebox.showinfo(APP_NAME, "\n".join(lines[-2:]))
    return 0


# ── entry ────────────────────────────────────────────────────────────────────
def parse(argv: list[str]) -> tuple[Options, dict[str, Any]]:
    flags = set(a for a in argv if a.startswith("--"))
    d = default_dir()
    if "--dir" in argv:
        d = Path(argv[argv.index("--dir") + 1])
    o = Options(
        install_dir=d,
        start_menu="--no-start-menu" not in flags,
        desktop="--no-desktop" not in flags,
        autostart="--autostart" in flags,
        ollama="--no-ollama" not in flags,
        stt="--no-stt" not in flags,
        launch="--launch" in flags,
    )
    return o, {"silent": "--silent" in flags, "uninstall": "--uninstall" in flags, "purge": "--purge" in flags}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    opts, mode = parse(argv)
    out = sys.stdout if sys.stdout is not None else None

    def con(line: str) -> None:
        if out is not None:
            with contextlib.suppress(Exception):
                print(line, file=out, flush=True)

    if mode["uninstall"]:
        if relaunch_from_temp(argv):
            return 0
        try:
            if mode["silent"]:
                uninstall(opts.install_dir, purge=mode["purge"], log=con)
                return 0
            return run_uninstall_gui(opts.install_dir)
        finally:
            delete_self_later()
    if mode["silent"]:
        inst = Installer(opts, con, lambda f, t: None)
        try:
            inst.run()
        except Exception as e:
            con(f"HIBA: {e}")
            if inst._file_log:
                inst._file_log.write(traceback.format_exc())
            return 1
        if opts.launch:
            inst.launch()
        return 0
    return run_gui(opts)


if __name__ == "__main__":
    sys.exit(main())
