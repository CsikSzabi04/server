"""Long-term memory (AI-2, spec 5.8): SQLite (WAL + FTS5) in data/mind/mind.db.

Every row carries `user_id`; every query is scoped by it. A guest has no user id here and
is never stored (the Mind checks the tier; `MemoryStore` refuses empty ids as a 2nd line).

Tables: turns (what was said; the dream phase digests them), facts (+ FTS5 index and an
optional embedding), profile_proposals (dream suggestions; enter the profile only when the
user accepts them on the HUD), meta (per-user bookkeeping).
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from rapidfuzz import fuzz

from ..mind.hu_text import norm
from .embed import cosine, from_blob, to_blob
from .redact import is_secret, mask

FactKind = Literal["fact", "preference", "person", "project", "summary", "note"]
MERGE_COSINE = 0.9  # spec 5.8: > 0.9 similarity → merge
MERGE_FUZZ = 90

_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, ts REAL NOT NULL, channel TEXT,
  request TEXT, reply TEXT, tools TEXT, llm_first_ms INTEGER, dreamed INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS turns_user_ts ON turns(user_id, ts);
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL,
  source TEXT, confidence REAL NOT NULL DEFAULT 0.7, mentions INTEGER NOT NULL DEFAULT 1,
  created REAL NOT NULL, updated REAL NOT NULL, embedding BLOB, profile INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS facts_user ON facts(user_id, kind);
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
  text, content='facts', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
  INSERT INTO facts_fts(facts_fts, rowid, text) VALUES ('delete', old.id, old.text); END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE OF text ON facts BEGIN
  INSERT INTO facts_fts(facts_fts, rowid, text) VALUES ('delete', old.id, old.text);
  INSERT INTO facts_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TABLE IF NOT EXISTS profile_proposals (
  id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, fact_id INTEGER, text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', created REAL NOT NULL, decided REAL);
CREATE TABLE IF NOT EXISTS meta (user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT, PRIMARY KEY (user_id, key));
"""


@dataclass(frozen=True)
class Fact:
    id: int
    text: str
    kind: str
    confidence: float
    mentions: int
    created: float
    updated: float
    profile: bool
    embedding: np.ndarray | None = None


@dataclass(frozen=True)
class Turn:
    id: int
    ts: float
    channel: str
    request: str
    reply: str
    tools: list[str]


def _need(user_id: str | None) -> str:
    if not user_id:
        raise ValueError("memory is for logged-in users only")
    return user_id


class MemoryStore:
    def __init__(self, db_path: Path | str, *, clock: Callable[[], float] = time.time) -> None:
        if str(db_path) != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._lock = threading.Lock()
        self._clock = clock
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _q(self, sql: str, args: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def _x(self, sql: str, args: tuple[Any, ...] = ()) -> int:
        """UPDATE / DELETE / upsert → number of affected rows."""
        with self._lock:
            return int(self._db.execute(sql, args).rowcount or 0)

    def _ins(self, sql: str, args: tuple[Any, ...] = ()) -> int:
        """INSERT → the new row id."""
        with self._lock:
            return int(self._db.execute(sql, args).lastrowid or 0)

    # ── turns ────────────────────────────────────────────────────────────────
    def add_turn(
        self,
        user_id: str,
        channel: str,
        request: str,
        reply: str,
        tools: list[str] | None = None,
        llm_first_ms: int | None = None,
    ) -> int:
        uid = _need(user_id)
        return self._ins(
            "INSERT INTO turns (user_id, ts, channel, request, reply, tools, llm_first_ms) VALUES (?,?,?,?,?,?,?)",
            (uid, self._clock(), channel, mask(request), mask(reply), json.dumps(tools or []), llm_first_ms),
        )

    def undreamed_turns(self, user_id: str, limit: int = 40) -> list[Turn]:
        rows = self._q(
            "SELECT id, ts, channel, request, reply, tools FROM turns WHERE user_id=? AND dreamed=0 ORDER BY ts LIMIT ?",
            (_need(user_id), limit),
        )
        return [Turn(r[0], r[1], r[2] or "", r[3] or "", r[4] or "", json.loads(r[5] or "[]")) for r in rows]

    def turns_since(self, user_id: str, since_ts: float) -> list[Turn]:
        rows = self._q(
            "SELECT id, ts, channel, request, reply, tools FROM turns WHERE user_id=? AND ts>=? ORDER BY ts",
            (_need(user_id), since_ts),
        )
        return [Turn(r[0], r[1], r[2] or "", r[3] or "", r[4] or "", json.loads(r[5] or "[]")) for r in rows]

    def mark_dreamed(self, user_id: str, ids: list[int]) -> None:
        for i in ids:
            self._x("UPDATE turns SET dreamed=1 WHERE user_id=? AND id=?", (_need(user_id), i))

    def prune_turns(self, user_id: str, keep_days: float) -> int:
        cutoff = self._clock() - keep_days * 86400
        return self._x("DELETE FROM turns WHERE user_id=? AND ts<?", (_need(user_id), cutoff))

    # ── facts ────────────────────────────────────────────────────────────────
    def _row(self, r: tuple[Any, ...]) -> Fact:
        return Fact(r[0], r[1], r[2], r[3], r[4], r[5], r[6], bool(r[7]), from_blob(r[8]))

    _COLS = "id, text, kind, confidence, mentions, created, updated, profile, embedding"

    def facts(self, user_id: str, kind: str | None = None, limit: int = 500) -> list[Fact]:
        if kind:
            rows = self._q(
                f"SELECT {self._COLS} FROM facts WHERE user_id=? AND kind=? ORDER BY updated DESC LIMIT ?",
                (_need(user_id), kind, limit),
            )
        else:
            rows = self._q(
                f"SELECT {self._COLS} FROM facts WHERE user_id=? ORDER BY updated DESC LIMIT ?", (_need(user_id), limit)
            )
        return [self._row(r) for r in rows]

    def get_fact(self, user_id: str, fact_id: int) -> Fact | None:
        rows = self._q(f"SELECT {self._COLS} FROM facts WHERE user_id=? AND id=?", (_need(user_id), fact_id))
        return self._row(rows[0]) if rows else None

    def add_fact(
        self,
        user_id: str,
        text: str,
        kind: str = "fact",
        *,
        source: str = "",
        confidence: float = 0.7,
        embedding: np.ndarray | None = None,
    ) -> tuple[int, bool] | None:
        """Insert, or merge into a near-duplicate (cosine > 0.9, or text ≥ 90 % similar).
        Returns (fact id, merged?) — or None if the text looks like a secret (never stored)."""
        uid = _need(user_id)
        text = " ".join(text.split()).strip()
        if not text or is_secret(text):
            return None
        dup = self._find_duplicate(uid, text, embedding)
        now = self._clock()
        if dup is not None:
            self._x(
                "UPDATE facts SET mentions=mentions+1, confidence=MIN(1.0, MAX(confidence, ?) + 0.1), updated=? "
                "WHERE user_id=? AND id=?",
                (confidence, now, uid, dup.id),
            )
            return dup.id, True
        fid = self._ins(
            "INSERT INTO facts (user_id, text, kind, source, confidence, created, updated, embedding) VALUES (?,?,?,?,?,?,?,?)",
            (uid, text, kind, source, confidence, now, now, to_blob(embedding) if embedding is not None else None),
        )
        return fid, False

    def _find_duplicate(self, uid: str, text: str, emb: np.ndarray | None) -> Fact | None:
        n = norm(text)
        best: tuple[float, Fact] | None = None
        for f in self.facts(uid, limit=2000):
            if f.kind == "summary":
                continue
            if emb is not None and f.embedding is not None and cosine(emb, f.embedding) > MERGE_COSINE:
                return f
            score = fuzz.ratio(n, norm(f.text))
            if score >= MERGE_FUZZ and (best is None or score > best[0]):
                best = (score, f)
        return best[1] if best else None

    def has_embeddings(self, user_id: str) -> bool:
        """Any fact with an embedding? (No → recall skips the embedding call: no latency.)"""
        return bool(self._q("SELECT 1 FROM facts WHERE user_id=? AND embedding IS NOT NULL LIMIT 1", (_need(user_id),)))

    def count_facts(self, user_id: str) -> int:
        return int(self._q("SELECT COUNT(*) FROM facts WHERE user_id=?", (_need(user_id),))[0][0])

    def set_embedding(self, user_id: str, fact_id: int, emb: np.ndarray) -> None:
        self._x("UPDATE facts SET embedding=? WHERE user_id=? AND id=?", (to_blob(emb), _need(user_id), fact_id))

    def delete_fact(self, user_id: str, fact_id: int) -> bool:
        uid = _need(user_id)
        self._x("DELETE FROM profile_proposals WHERE user_id=? AND fact_id=?", (uid, fact_id))
        return self._x("DELETE FROM facts WHERE user_id=? AND id=?", (uid, fact_id)) > 0

    def forget_everything(self, user_id: str) -> None:
        uid = _need(user_id)
        for table in ("facts", "turns", "profile_proposals", "meta"):
            self._x(f"DELETE FROM {table} WHERE user_id=?", (uid,))

    # ── recall ───────────────────────────────────────────────────────────────
    def search(
        self, user_id: str, query: str, *, k: int = 5, query_emb: np.ndarray | None = None, min_score: float = 0.35
    ) -> list[tuple[Fact, float]]:
        """Hybrid: FTS5 (BM25) + cosine (if embeddings) + small boosts for mentions/profile and
        a gentle recency decay (a week-old preference must still win — DoD M4)."""
        uid = _need(user_id)
        # Crude Hungarian stemming: suffixes make the query word longer than the stored one
        # ("rövidek" vs "rövid"), so search 5-letter prefixes ("rovid*", "valas*").
        words = list(dict.fromkeys(w[:5] for w in re.findall(r"\w{3,}", norm(query))))[:12]
        fts: dict[int, float] = {}
        if words:
            match = " OR ".join(f'"{w}"*' for w in words)
            try:
                rows = self._q(
                    "SELECT f.id, bm25(facts_fts) FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid "
                    "WHERE facts_fts MATCH ? AND f.user_id=? ORDER BY bm25(facts_fts) LIMIT 30",
                    (match, uid),
                )
            except sqlite3.OperationalError:
                rows = []
            if rows:
                worst = max(-r[1] for r in rows) or 1.0
                fts = {r[0]: (-r[1]) / worst for r in rows}  # 0..1, higher = better
        now = self._clock()
        scored: list[tuple[Fact, float]] = []
        for f in self.facts(uid, limit=2000):
            s_fts = fts.get(f.id, 0.0)
            s_emb = cosine(query_emb, f.embedding) if (query_emb is not None and f.embedding is not None) else 0.0
            if s_fts == 0.0 and s_emb < 0.5:
                continue
            age_days = max(0.0, (now - f.updated) / 86400)
            score = 0.6 * s_fts + 0.8 * max(0.0, s_emb - 0.3) / 0.7 + 0.05 * min(f.mentions, 5) + (0.1 if f.profile else 0.0)
            score *= 1.0 / (1.0 + age_days / 60.0)  # 1 week → ×0.9; 2 months → ×0.5
            if score >= min_score:
                scored.append((f, round(score, 3)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def standing_preferences(self, user_id: str, k: int = 3) -> list[Fact]:
        """Preferences that apply to every answer (used spontaneously, not only on keyword hit)."""
        rows = self._q(
            f"SELECT {self._COLS} FROM facts WHERE user_id=? AND kind='preference' AND profile=0 "
            "ORDER BY mentions DESC, confidence DESC, updated DESC LIMIT ?",
            (_need(user_id), k),
        )
        return [self._row(r) for r in rows]

    def profile_facts(self, user_id: str) -> list[str]:
        rows = self._q("SELECT text FROM facts WHERE user_id=? AND profile=1 ORDER BY id", (_need(user_id),))
        return [r[0] for r in rows]

    # ── proposals ────────────────────────────────────────────────────────────
    def add_proposal(self, user_id: str, fact_id: int, text: str) -> int | None:
        uid = _need(user_id)
        if self._q("SELECT 1 FROM profile_proposals WHERE user_id=? AND fact_id=?", (uid, fact_id)):
            return None  # proposed once already (accepted or rejected) → never again
        return self._ins(
            "INSERT INTO profile_proposals (user_id, fact_id, text, created) VALUES (?,?,?,?)",
            (uid, fact_id, text, self._clock()),
        )

    def pending_proposals(self, user_id: str) -> list[tuple[int, str]]:
        return [
            (r[0], r[1])
            for r in self._q(
                "SELECT id, text FROM profile_proposals WHERE user_id=? AND status='pending' ORDER BY id", (_need(user_id),)
            )
        ]

    def decide(self, user_id: str, proposal_id: int, accept: bool) -> bool:
        """Only the user's explicit answer changes the profile (never the dream phase itself)."""
        uid = _need(user_id)
        rows = self._q("SELECT fact_id FROM profile_proposals WHERE user_id=? AND id=? AND status='pending'", (uid, proposal_id))
        if not rows:
            return False
        self._x(
            "UPDATE profile_proposals SET status=?, decided=? WHERE user_id=? AND id=?",
            ("accepted" if accept else "rejected", self._clock(), uid, proposal_id),
        )
        if accept and rows[0][0] is not None:
            self._x("UPDATE facts SET profile=1 WHERE user_id=? AND id=?", (uid, rows[0][0]))
        return True

    # ── meta ─────────────────────────────────────────────────────────────────
    def get_meta(self, user_id: str, key: str) -> str | None:
        rows = self._q("SELECT value FROM meta WHERE user_id=? AND key=?", (_need(user_id), key))
        return rows[0][0] if rows else None

    def set_meta(self, user_id: str, key: str, value: str) -> None:
        self._x(
            "INSERT INTO meta (user_id, key, value) VALUES (?,?,?) ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
            (_need(user_id), key, value),
        )
