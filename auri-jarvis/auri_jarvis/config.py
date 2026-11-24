"""auri_jarvis.config — load + merge the YAML configs and the .env (owner: AI-3).

One merged dict is handed to every factory (`create_ears/create_mouth/create_mind`):

    jarvis.yaml (AI-3, required) ← audio.yaml (AI-1) ← mind.yaml (AI-2)   [deep-merged]
    cfg["env"]   = .env values (+ process env overrides); sensitive ones wrapped in `Secret`
    cfg["paths"] = root / config_dir / data_dir / loaded / missing  (reserved, set here)

`${VAR}` and `${VAR:-default}` inside any YAML string are substituted from cfg["env"].
Each AI reads only its own sections (see JARVIS_BUILD §2.2).

Secrets: `Secret` is a `str` whose repr() is masked, so printing / logging the cfg dict never
leaks a key. `install_log_redaction()` additionally scrubs known secret values from every log
record. Use the value normally (headers, f-strings) — str() is the real value on purpose.
"""

from __future__ import annotations

import copy
import logging
import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # …/auri-jarvis
CONFIG_FILES: tuple[str, ...] = ("jarvis.yaml", "audio.yaml", "mind.yaml")  # merge order
REQUIRED_FILES: tuple[str, ...] = ("jarvis.yaml",)
RESERVED_KEYS = ("env", "paths")

# Env keys we always pick up from the process environment (they override .env).
KNOWN_ENV_KEYS = (
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_MODEL_ID",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "JARVIS_HUD_TOKEN",
    "JARVIS_INPUT_DEVICE",
)
_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD)", re.IGNORECASE)
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


class ConfigError(RuntimeError):
    """Raised for a missing required file or invalid YAML — message is user-facing (HU)."""


class Secret(str):
    """A str whose repr() is masked. str()/format() still return the real value."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "Secret('***')" if self else "Secret('')"


def is_secret_name(name: str) -> bool:
    return bool(_SECRET_NAME.search(name))


# ── log redaction ────────────────────────────────────────────────────────────
_KNOWN_SECRETS: set[str] = set()


def register_secret(value: str | None) -> None:
    """Remember a secret value so log records containing it get scrubbed."""
    if value and len(value) >= 6:
        _KNOWN_SECRETS.add(str(value))


def redact(text: str) -> str:
    for s in sorted(_KNOWN_SECRETS, key=len, reverse=True):
        if s in text:
            text = text.replace(s, "***")
    return text


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _KNOWN_SECRETS:
            try:
                msg = record.getMessage()
            except Exception:
                return True
            clean = redact(msg)
            if clean != msg:
                record.msg, record.args = clean, None
        return True


_FILTER = _RedactFilter()


def install_log_redaction(*loggers: logging.Logger) -> None:
    """Attach the redaction filter to the given loggers' handlers (default: root handlers)."""
    targets = loggers or (logging.getLogger(),)
    for lg in targets:
        for h in lg.handlers:
            if _FILTER not in h.filters:
                h.addFilter(_FILTER)


# ── helpers ──────────────────────────────────────────────────────────────────
def deep_merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge `over` into a copy of `base` (dicts merge, everything else replaces)."""
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _substitute(value: Any, env: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        hit_secret = False

        def repl(m: re.Match[str]) -> str:
            nonlocal hit_secret
            name, default = m.group(1), m.group(2)
            v = env.get(name) or ""
            if not v and default is not None:
                v = default
            if isinstance(v, Secret) and v:
                hit_secret = True
            return str(v)

        out = _VAR.sub(repl, value)
        return Secret(out) if hit_secret else out
    if isinstance(value, dict):
        return {k: _substitute(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, env) for v in value]
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Nem olvasható a konfigfájl: {path} ({e})") from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (sor {mark.line + 1}, oszlop {mark.column + 1})" if mark else ""
        raise ConfigError(f"Hibás YAML: {path}{where}: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"A {path.name} gyökere nem leképezés (mapping), hanem {type(data).__name__}.")
    return data


def load_env(env_file: Path | None, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Read .env (missing file = empty) and overlay process env for known/JARVIS_* keys."""
    environ = os.environ if environ is None else environ
    raw: dict[str, str] = {}
    if env_file is not None and env_file.is_file():
        raw = {k: (v or "") for k, v in dotenv_values(env_file).items()}
    for k, v in environ.items():
        if k in KNOWN_ENV_KEYS or k.startswith("JARVIS_") or k in raw:
            raw[k] = v
    env: dict[str, str] = {}
    for k, v in raw.items():
        v = v.strip()
        if is_secret_name(k):
            env[k] = Secret(v)
            register_secret(v)
        else:
            env[k] = v
    return env


def load_config(
    root: Path | str | None = None,
    *,
    config_dir: Path | str | None = None,
    env_file: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
    required: Iterable[str] = REQUIRED_FILES,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load jarvis.yaml + audio.yaml + mind.yaml + .env into one dict.

    Missing *required* file → ConfigError (clear Hungarian message). Missing optional file →
    warning + listed in cfg["paths"]["missing"] (AI-1/AI-2 may not have created theirs yet).
    """
    root_p = Path(root) if root is not None else PROJECT_ROOT
    cdir = Path(config_dir) if config_dir is not None else root_p / "config"
    envf = Path(env_file) if env_file is not None else root_p / ".env"
    required = tuple(required)

    env = load_env(envf, environ)
    merged: dict[str, Any] = {}
    owners: dict[str, str] = {}
    loaded: list[str] = []
    missing: list[str] = []
    for name in CONFIG_FILES:
        path = cdir / name
        if not path.is_file():
            if name in required:
                raise ConfigError(
                    f"Hiányzó konfigfájl: {path}. Ez kötelező — a repóban lévő mintát "
                    f"(config/{name}) állítsd vissza, vagy add meg a --config-dir kapcsolót."
                )
            log.warning("config: %s not found — its sections stay empty", name)
            missing.append(name)
            continue
        data = _read_yaml(path)
        for key in data:
            if key in RESERVED_KEYS:
                raise ConfigError(f"A '{key}' kulcs foglalt (config.py tölti ki) — ne szerepeljen a {name}-ben.")
            if key in owners:
                log.warning("config: section '%s' defined in both %s and %s (later wins)", key, owners[key], name)
            owners[key] = name
        merged = deep_merge(merged, data)
        loaded.append(name)

    merged = _substitute(merged, env)
    if overrides:
        merged = deep_merge(merged, overrides)

    data_dir = root_p / "data"
    merged["env"] = env
    merged["paths"] = {
        "root": str(root_p),
        "config_dir": str(cdir),
        "data_dir": str(data_dir),
        "env_file": str(envf),
        "loaded": loaded,
        "missing": missing,
    }
    return merged


def get(cfg: Mapping[str, Any], dotted: str, default: Any = None) -> Any:
    """Read a nested value: get(cfg, "hud.port", 8790)."""
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def data_path(cfg: Mapping[str, Any], *parts: str, create: bool = True) -> Path:
    """Path under data/ (AI-3 writes only to data/body/ — pass "body", ...)."""
    p = Path(cfg["paths"]["data_dir"]).joinpath(*parts)
    if create:
        (p if not p.suffix else p.parent).mkdir(parents=True, exist_ok=True)
    return p


def describe(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """A printable copy: secrets replaced by '***' (or '' if empty)."""

    def walk(v: Any) -> Any:
        if isinstance(v, Secret):
            return "***" if v else ""
        if isinstance(v, Mapping):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v

    return walk(cfg)
