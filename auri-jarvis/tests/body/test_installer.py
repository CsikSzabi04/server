"""Installer gates (AI-3): what may / may not go into the public setup, the secret scanner, the
Supabase-key check, CLI flags, and the uninstaller's keep-my-data logic. No real install here."""

from __future__ import annotations

import base64
import json
import sys
import zipfile
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
sys.path.insert(0, str(INSTALLER))

import build_installer as B  # noqa: E402
import setup_app as S  # noqa: E402


def make_tree(root: Path) -> tuple[Path, Path]:
    aj = root / "auri-jarvis"
    files = {
        "auri_jarvis/__init__.py": "x",
        "auri_jarvis/hud/server.py": "x",
        "auri_jarvis/__pycache__/x.cpython-312.pyc": "x",
        "config/jarvis.yaml": "a: 1",
        "config/me.md": "PERSONAL PROFILE",
        "scripts/smoke.py": "x",
        "requirements.txt": "x",
        ".env": "ELEVENLABS_API_KEY=sk_live_SUPERSECRET_123",
        ".env.example": "ELEVENLABS_API_KEY=",
        "data/body/identity.db": "user cache",
        "tests/body/test_x.py": "x",
        "prompts/jarvis-ai-3-body.md": "x",
        ".venv/Lib/site.py": "x",
        "models/piper/x.onnx": "x",
    }
    for rel, txt in files.items():
        p = aj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    dist = root / "web" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return aj, dist


def test_payload_includes_code_and_excludes_private_files(tmp_path: Path):
    aj, dist = make_tree(tmp_path)
    out = tmp_path / "payload.zip"
    names = set(B.build_payload(out, root=aj, web_dist=dist))
    assert "auri-jarvis/auri_jarvis/hud/server.py" in names
    assert "auri-jarvis/config/jarvis.yaml" in names
    assert "auri-jarvis/.env.example" in names
    assert "web/dist/index.html" in names and "web/dist/assets/app.js" in names
    for bad in ("me.md", "/.env", "/data/", "/tests/", "/prompts/", "/.venv/", "__pycache__", "/models/"):
        assert not any(bad in "/" + n for n in names if not n.endswith(".env.example")), bad


def test_secret_scanner_catches_a_leak(tmp_path: Path):
    z = tmp_path / "p.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("a.txt", "nothing here")
        zf.writestr("web/dist/x.js", "const k='sk_live_SUPERSECRET_123'")
    assert B.scan_for_secrets(z, ["sk_live_SUPERSECRET_123"]) == ["web/dist/x.js"]
    assert B.scan_for_secrets(z, ["other"]) == []


def _jwt(role: str) -> str:
    def b(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return f"{b({'alg': 'HS256'})}.{b({'role': role})}.sig"


@pytest.mark.parametrize(
    ("key", "ok"),
    [
        ("sb_publishable_abc123", True),
        (_jwt("anon"), True),
        ("sb_secret_abc", False),
        (_jwt("service_role"), False),
        ("weird", False),
    ],
)
def test_env_defaults_only_accepts_public_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, ok: bool):
    web = tmp_path / "web"
    web.mkdir()
    (web / ".env.local").write_text(
        f"VITE_SUPABASE_URL=https://x.supabase.co\nVITE_SUPABASE_ANON_KEY={key}\nGROQ_API_KEY=secret\n"
    )
    monkeypatch.setattr(B, "WEB", web)
    if ok:
        out = B.env_defaults()
        assert "SUPABASE_URL=https://x.supabase.co" in out and f"SUPABASE_ANON_KEY={key}" in out and "GROQ" not in out
    else:
        with pytest.raises(SystemExit):
            B.env_defaults()


def test_setup_cli_flags():
    o, mode = S.parse(["--silent", "--dir", r"C:\X", "--no-ollama", "--no-autostart"])
    assert mode["silent"] and not mode["uninstall"]
    assert o.install_dir == Path(r"C:\X") and not o.ollama and not o.autostart and o.start_menu and o.stt
    o, mode = S.parse(["--uninstall", "--purge"])
    assert mode["uninstall"] and mode["purge"] and o.install_dir == S.default_dir()


def test_uninstall_keeps_personal_data_unless_purged(tmp_path: Path):
    d = tmp_path / "AuriJarvis"
    for rel in (
        "app/auri-jarvis/data/body/identity.db",
        "app/auri-jarvis/.env",
        "app/auri-jarvis/auri_jarvis/x.py",
        "tools/uv.exe",
    ):
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    S._remove_tree(d, {d / "app" / "auri-jarvis" / "data", d / "app" / "auri-jarvis" / ".env"})
    assert (d / "app/auri-jarvis/data/body/identity.db").exists() and (d / "app/auri-jarvis/.env").exists()
    assert not (d / "tools").exists() and not (d / "app/auri-jarvis/auri_jarvis").exists()
    S._remove_tree(d, set())
    assert not d.exists()
