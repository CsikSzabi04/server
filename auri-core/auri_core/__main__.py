"""CLI entry: `python -m auri_core <command> …` (owner: AI-3).

Subcommands are imported lazily, so a missing module (e.g. `bench` before AI-2 ships it)
only breaks its own command, never the others.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable

# command → (module, function, one-line help). The function takes argv (list[str]) → exit code.
COMMANDS: dict[str, tuple[str, str, str]] = {
    "run": ("auri_core.solve", "main_run", "egy feladat megoldása: run tasks/py-l1-0001"),
    "bench": ("auri_core.bench", "main_bench", "mérés a feladatkészleten: bench --mode model-only --split dev --lang py"),
    "config": ("auri_core.config", "main_config", "a betöltött beállítások kiírása (titkok nélkül)"),
    "serve": ("auri_core.server", "main_serve", "a helyi szolgáltatás indítása (127.0.0.1:8791, P1)"),
    "migrate-seeds": ("auri_core.migrate.seeds", "main_migrate_seeds", "a web BRAIN seedjeinek átvétele a közös tudásba (P1)"),
}


def _usage() -> str:
    lines = ["Használat: python -m auri_core <parancs> [argumentumok]", "", "Parancsok:"]
    lines += [f"  {name:<8} {help_}" for name, (_, _, help_) in COMMANDS.items()]
    return "\n".join(lines)


def _resolve(command: str) -> Callable[[list[str]], int]:
    module_name, func_name, _ = COMMANDS[command]
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows console (cp1250) would garble or crash on accents/arrows
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_usage())
        return 0
    command, rest = args[0], args[1:]
    if command not in COMMANDS:
        print(f"Ismeretlen parancs: {command}\n\n{_usage()}", file=sys.stderr)
        return 2
    try:
        func = _resolve(command)
    except (ImportError, AttributeError) as e:
        print(f"A(z) „{command}” parancs még nem érhető el ({COMMANDS[command][0]}): {e}", file=sys.stderr)
        return 3
    return int(func(rest) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
