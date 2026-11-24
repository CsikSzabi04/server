"""Timers + reminders (AI-2). Survive restarts (SQLite, data/mind/mind.db); on expiry an
`Event("say", …)` goes to the orchestrator (JARVIS_BUILD 2.3).

Privacy (user rule, see memory "privacy-personal-data-rule"): a guest's timers live in
RAM only and are dropped on identity change; a user's timers are keyed by user id, and a
label is spoken only while that same identity is active — otherwise a neutral sentence.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..contracts import Emit, Event, UserContext

log = logging.getLogger(__name__)

Kind = Literal["timer", "reminder"]


@dataclass(frozen=True)
class TimerItem:
    id: int
    owner: str
    kind: Kind
    due: float  # epoch seconds
    text: str
    persistent: bool


def owner_key(user: UserContext) -> str:
    return f"user:{user.user_id}" if user.tier == "user" and user.user_id else "guest"


class TimerService:
    def __init__(self, db_path: Path | None, emit: Emit, *, clock: Callable[[], float] = time.time) -> None:
        self._emit = emit
        self._clock = clock
        self._items: dict[int, TimerItem] = {}
        self._ram_id = -1  # RAM-only items get negative ids
        self._db: sqlite3.Connection | None = None
        if db_path is not None:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS timers (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,"
                " kind TEXT NOT NULL, due REAL NOT NULL, text TEXT NOT NULL, created REAL NOT NULL)"
            )
            for row in self._db.execute("SELECT id, owner, kind, due, text FROM timers"):
                self._items[row[0]] = TimerItem(row[0], row[1], row[2], row[3], row[4], True)
        self.current_owner = "guest"
        self._wake: asyncio.Event | None = None
        self._task: asyncio.Task[None] | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._task is None:
            self._wake = asyncio.Event()
            self._task = asyncio.get_running_loop().create_task(self._loop(), name="mind-timers")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._db:
            self._db.close()
            self._db = None

    # ── API used by the tools ────────────────────────────────────────────────
    def now(self) -> float:
        return self._clock()

    def add(self, owner: str, kind: Kind, due: float, text: str, *, persist: bool) -> TimerItem:
        if persist and self._db is not None:
            cur = self._db.execute(
                "INSERT INTO timers (owner, kind, due, text, created) VALUES (?, ?, ?, ?, ?)",
                (owner, kind, due, text, self._clock()),
            )
            item = TimerItem(int(cur.lastrowid or 0), owner, kind, due, text, True)
        else:
            item = TimerItem(self._ram_id, owner, kind, due, text, False)
            self._ram_id -= 1
        self._items[item.id] = item
        self._kick()
        return item

    def list(self, owner: str, kind: Kind | None = None) -> list[TimerItem]:
        return sorted(
            (i for i in self._items.values() if i.owner == owner and (kind is None or i.kind == kind)),
            key=lambda i: i.due,
        )

    def cancel(self, owner: str, item_id: int | None = None, kind: Kind | None = None) -> int:
        victims = [i for i in self.list(owner, kind) if item_id is None or i.id == item_id]
        for i in victims:
            self._remove(i)
        self._kick()
        return len(victims)

    def switch_owner(self, owner: str) -> None:
        """Identity changed: drop the guest's RAM timers (they never outlive a switch)."""
        for i in [i for i in self._items.values() if i.owner == "guest"]:
            self._remove(i)
        self.current_owner = owner
        self._kick()

    # ── internals ────────────────────────────────────────────────────────────
    def _remove(self, item: TimerItem) -> None:
        self._items.pop(item.id, None)
        if item.persistent and self._db is not None:
            self._db.execute("DELETE FROM timers WHERE id = ?", (item.id,))

    def _kick(self) -> None:
        if self._wake is not None:
            self._wake.set()

    def fire_due(self) -> list[TimerItem]:
        """Announce every item that is due now (also items missed while switched off)."""
        now = self._clock()
        due = sorted((i for i in self._items.values() if i.due <= now), key=lambda i: i.due)
        for item in due:
            self._remove(item)
            self._emit(Event("say", {"text": self._announcement(item)}))
        return due

    def _announcement(self, item: TimerItem) -> str:
        mine = item.owner == self.current_owner
        if item.kind == "timer":
            return f"Lejárt az időzítő: {item.text}." if mine and item.text else "Lejárt egy időzítő."
        if mine:
            return f"Emlékeztető: {item.text}."
        return "Van egy emlékeztető. A meghallgatásához jelentkezz be."

    async def _loop(self) -> None:
        assert self._wake is not None
        while True:
            self.fire_due()
            nxt = min((i.due for i in self._items.values()), default=None)
            timeout = None if nxt is None else max(0.05, min(nxt - self._clock(), 60.0))
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout)
            except TimeoutError:
                pass
