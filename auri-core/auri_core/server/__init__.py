"""Local HTTP service (owner: AI-3, P1). Spec: thinking/01-architektura/03-hol-fut-auri-core.md §4.

Only on 127.0.0.1; every request passes Host → Origin → token checks (app.py)."""

from .app import create_app, load_or_create_token, main_serve

__all__ = ["create_app", "load_or_create_token", "main_serve"]
