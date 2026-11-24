"""auri_jarvis.state — the daemon state machine (spec §4.2, owner: AI-3).

IDLE → LISTENING → TRANSCRIBING → THINKING/ACTING → SPEAKING → IDLE, plus barge-in
(SPEAKING → LISTENING) and the follow-up window (after a reply, listen again without a wake
word for a few seconds). Every change emits a `state` event: {state, since, prev, follow_up}.

The machine is permissive on purpose: an unexpected transition is logged (so it shows up in
tests/logs) but still applied — a voice daemon must never wedge because of an ordering race.
Going to IDLE is always allowed.
"""

from __future__ import annotations

import enum
import logging
import time

from .contracts import Emit, Event

log = logging.getLogger(__name__)


class State(enum.StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ACTING = "acting"


S = State
ALLOWED: dict[State, frozenset[State]] = {
    S.IDLE: frozenset({S.LISTENING, S.THINKING, S.ACTING, S.SPEAKING}),
    S.LISTENING: frozenset({S.TRANSCRIBING, S.THINKING, S.SPEAKING}),
    S.TRANSCRIBING: frozenset({S.THINKING, S.ACTING, S.LISTENING}),
    S.THINKING: frozenset({S.SPEAKING, S.ACTING, S.LISTENING}),
    S.ACTING: frozenset({S.SPEAKING, S.THINKING, S.LISTENING}),
    S.SPEAKING: frozenset({S.LISTENING, S.THINKING, S.ACTING}),
}


class StateMachine:
    def __init__(self, emit: Emit) -> None:
        self._emit = emit
        self.state = State.IDLE
        self.since = time.time()
        self.follow_up = False
        self.unexpected: list[tuple[State, State]] = []
        self.history: list[State] = [State.IDLE]

    def set(self, new: State, *, follow_up: bool = False) -> bool:
        """Change state; returns False if it was already in `new` (no event)."""
        new = State(new)
        if new == self.state and follow_up == self.follow_up:
            return False
        prev = self.state
        if new != prev and new != State.IDLE and new not in ALLOWED[prev]:
            self.unexpected.append((prev, new))
            log.warning("state: unexpected transition %s → %s (applied)", prev.value, new.value)
        self.state, self.follow_up, self.since = new, follow_up, time.time()
        self.history.append(new)
        if len(self.history) > 200:
            del self.history[:100]
        self._emit(
            Event(
                "state",
                {"state": new.value, "since": self.since, "prev": prev.value, "follow_up": follow_up},
            )
        )
        return True

    def announce(self) -> None:
        """Re-emit the current state (e.g. at startup)."""
        self._emit(
            Event(
                "state",
                {"state": self.state.value, "since": self.since, "prev": None, "follow_up": self.follow_up},
            )
        )

    @property
    def idle(self) -> bool:
        return self.state == State.IDLE
