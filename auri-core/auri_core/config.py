"""Configuration: paths, Ollama URL, model names (owner: AI-3).

Every value has a default and can be overridden by an environment variable (or by
`auri-core/.env`, which never overrides a variable that is already set). Stdlib only.

    from auri_core.config import load_config
    cfg = load_config()            # cached; load_config(reload=True) re-reads env
    cfg.db_path, cfg.runs_dir, cfg.ollama_url, cfg.models.code
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parent.parent  # …/auri-core
REPO_ROOT = CORE_ROOT.parent

ENV_PREFIX = "AURI_CORE_"
# Names that must never be printed or passed on (logs, sandbox env, model prompts).
SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "SUPABASE_")


def _local_appdata() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) if base else Path.home() / "AppData" / "Local"


@dataclass(frozen=True)
class Models:
    code: str = "gemma4:e2b"  # P0 default for L0–L1 (router may choose otherwise, P6)
    roles: str = "qwen3.5:4b"  # NK20 proposal; RAM not measured yet (NK14 h)
    embed: str = "embeddinggemma"
    l3: str | None = None  # P6: stronger local model for escalation; None = none measured/installed (router skips)


@dataclass(frozen=True)
class Config:
    data_dir: Path
    db_path: Path
    runs_dir: Path  # data/runs/<runId>/journal.jsonl — the solve() journal
    sandbox_runs_dir: Path  # OUTSIDE the repo (S0): %LOCALAPPDATA%\Auri\sandbox\runs
    sandbox_runtime_dir: Path  # dedicated node.exe / python.exe behind the firewall rule
    tasks_dir: Path
    ollama_url: str
    models: Models = field(default_factory=Models)
    keep_alive: str = "10m"  # Core default; VOICE (Jarvis) keeps its own model warm
    request_timeout_s: float = 300.0
    connect_timeout_s: float = 3.0
    num_ctx: int = 8192
    server_host: str = "127.0.0.1"  # P1 (NK1, NK21: local only)
    server_port: int = 8791
    # browser origins allowed to call the server (AuriGPT dev/prod); empty = no browser access
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    # P1 identity (01/03 §4): X-Auri-User is checked via GET {supabase_url}/auth/v1/user; unset → everyone is a guest
    supabase_url: str = ""
    supabase_anon_key: str = field(default="", repr=False)
    users_dir: Path = Path("data/users")
    # P6 router (08/02): cloud fallback stays off unless the user turns it on (08/03, NK)
    cloud_mode: str = "off"  # off | ask | auto_general (08/03 §2)
    cloud_model: str | None = None
    ram_budget_gb: float = 5.0
    # P4 background (05/02): off | light (no model: maintenance, dedupe, audit) | full (+ model jobs at night)
    background: str = "light"
    # P6 cloud keys (08/03): only in auri-core/.env, never logged, never in a prompt
    groq_api_key: str = field(default="", repr=False)
    gemini_api_key: str = field(default="", repr=False)
    gemini_paid: bool = False  # Gemini only with a paid project (same GEMINI_PAID=1 rule as the web chat proxy)
    cloud_daily_cap: int = 20  # per user per day — the cloud must not quietly become the default  # models above this (est. RAM) are never routed to  # T1: one SQLite file per signed-in user (hashed id)

    def public_dict(self) -> dict[str, object]:
        """For `python -m auri_core config` — no secrets live here, paths as strings."""
        d = asdict(self)
        for k in ("supabase_anon_key", "groq_api_key", "gemini_api_key"):
            d[k] = "[beállítva]" if d[k] else ""
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in d.items()}


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parser (comments, blank lines, optional quotes)."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def _env(name: str, default: str, env: dict[str, str]) -> str:
    v = env.get(ENV_PREFIX + name)
    return v if v not in (None, "") else default


def build_config(env: dict[str, str] | None = None) -> Config:
    """Pure: build a Config from an env mapping (tests pass their own)."""
    e = dict(os.environ if env is None else env)
    data_dir = Path(_env("DATA_DIR", str(CORE_ROOT / "data"), e))
    return Config(
        data_dir=data_dir,
        db_path=Path(_env("DB_PATH", str(data_dir / "core.db"), e)),
        runs_dir=Path(_env("RUNS_DIR", str(data_dir / "runs"), e)),
        sandbox_runs_dir=Path(_env("SANDBOX_RUNS_DIR", str(_local_appdata() / "Auri" / "sandbox" / "runs"), e)),
        sandbox_runtime_dir=Path(_env("SANDBOX_RUNTIME_DIR", r"C:\AuriSandbox\runtime", e)),
        tasks_dir=Path(_env("TASKS_DIR", str(CORE_ROOT / "tasks"), e)),
        ollama_url=_env("OLLAMA_URL", e.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434"), e).rstrip("/"),
        models=Models(
            code=_env("MODEL_CODE", Models.code, e),
            roles=_env("MODEL_ROLES", Models.roles, e),
            embed=_env("MODEL_EMBED", Models.embed, e),
            l3=_env("MODEL_L3", "", e) or None,
        ),
        keep_alive=_env("KEEP_ALIVE", "10m", e),
        request_timeout_s=float(_env("REQUEST_TIMEOUT_S", "300", e)),
        connect_timeout_s=float(_env("CONNECT_TIMEOUT_S", "3", e)),
        num_ctx=int(_env("NUM_CTX", "8192", e)),
        server_host=_env("HOST", "127.0.0.1", e),
        server_port=int(_env("PORT", "8791", e)),
        supabase_url=_env("SUPABASE_URL", "", e).rstrip("/"),
        supabase_anon_key=_env("SUPABASE_ANON_KEY", "", e),
        users_dir=Path(_env("USERS_DIR", str(data_dir / "users"), e)),
        cloud_mode=_env("CLOUD_MODE", "off", e) if _env("CLOUD_MODE", "off", e) in ("off", "ask", "auto_general") else "off",
        cloud_model=_env("CLOUD_MODEL", "", e) or None,
        ram_budget_gb=float(_env("RAM_BUDGET_GB", "5", e)),
        groq_api_key=_env("GROQ_API_KEY", "", e),
        gemini_api_key=_env("GEMINI_API_KEY", "", e),
        gemini_paid=_env("GEMINI_PAID", "0", e) == "1",
        cloud_daily_cap=int(_env("CLOUD_DAILY_CAP", "20", e)),
        background=_env("BACKGROUND", "light", e) if _env("BACKGROUND", "light", e) in ("off", "light", "full") else "light",
        allowed_origins=tuple(o.strip().rstrip("/") for o in _env("ORIGINS", "http://localhost:5173,http://127.0.0.1:5173", e).split(",") if o.strip()),
    )


@lru_cache(maxsize=1)
def _cached() -> Config:
    for k, v in _read_dotenv(CORE_ROOT / ".env").items():
        os.environ.setdefault(k, v)
    return build_config()


def load_config(*, reload: bool = False) -> Config:
    if reload:
        _cached.cache_clear()
    return _cached()


def is_secret_env_name(name: str) -> bool:
    up = name.upper()
    return any(m in up for m in SECRET_ENV_MARKERS) or up.endswith("_API_KEY")


def main_config(argv: list[str]) -> int:
    del argv
    for k, v in load_config().public_dict().items():
        print(f"{k:<20} {v}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_config(sys.argv[1:]))
