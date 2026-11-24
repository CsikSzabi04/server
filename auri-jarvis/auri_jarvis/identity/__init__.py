"""auri_jarvis.identity — who is talking to Auri: login bridge, prefs, guest mode (owner: AI-3)."""

from .prefs import (
    PrefsError,
    apply_partial,
    guest_prefs,
    guest_user,
    prefs_from_dict,
    prefs_to_dict,
    validate_partial,
)

__all__ = [
    "PrefsError",
    "apply_partial",
    "guest_prefs",
    "guest_user",
    "prefs_from_dict",
    "prefs_to_dict",
    "validate_partial",
]
