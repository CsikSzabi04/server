"""Knowledge store — SQLite WAL + FTS5 (owner: AI-3).

Spec: thinking/01-architektura/04-tarolas-es-adatfolyam.md (schema, statuses, provenance),
thinking/06-programozas/03-kod-tudasbazis.md (VerifiedSnippet), 06/06 §7 (ErrorPattern).

Rules enforced here (each has a test in tests/body/test_store.py):
  * every write goes through the privacy gate (`privacy.guard`) — no exceptions;
  * a code snippet enters only with a green run (`verification.status == "pass"`) → `verified`;
  * no item without provenance; `generated_by model` alone never makes anything `verified`;
  * the same task a second time → `find_snippet_for_task()` hit, 0 LLM calls (cache key:
    `task_signature`);
  * episodes are append-only.

Inputs are duck-typed (dataclass or dict) until `contracts.py` (AI-1) is published; field
names follow the spec. Methods are `async` to match the `KnowledgeStore` Protocol; the
work itself is local, synchronous sqlite3 (one connection, one event loop).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from . import privacy
from .contracts import (
    ErrorCause,
    ErrorFix,
    ErrorPattern,
    PatternSource,
    Provenance,
    SnippetEnv,
    SnippetSource,
    SnippetTest,
    SnippetUsage,
    SnippetVerification,
    VerifiedSnippet,
)

SCHEMA_VERSION = 1
STATUSES = ("hypothesis", "verified", "contested", "stale", "refuted", "archived")
STATUS_WEIGHT = {"verified": 1.0, "hypothesis": 0.4, "contested": 0.2, "stale": 0.2}  # refuted/archived: filtered
LICENSE_UNKNOWN = {"", "unknown", "none", None}
CODE_KINDS = frozenset({"code", "recipe"})  # knowledge items whose body is code → privacy "code" profile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cloud_audit (                -- 08/03 §4: what left the machine (already masked), 30 days
  at TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, purpose TEXT NOT NULL, chars INTEGER NOT NULL,
  redactions INTEGER NOT NULL, sha256 TEXT NOT NULL, text TEXT NOT NULL, ok INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cloud_quota (                -- 08/03 §5: calls per provider/day, per user/day
  day TEXT NOT NULL, key TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0, exhausted_until TEXT,
  PRIMARY KEY (day, key));
CREATE TABLE IF NOT EXISTS search_cache (
  key TEXT PRIMARY KEY, hits TEXT NOT NULL, stored_at REAL NOT NULL, ttl_s REAL NOT NULL);

CREATE TABLE IF NOT EXISTS knowledge_items (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, lang TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'hypothesis', verification TEXT, trust REAL NOT NULL DEFAULT 0.3,
  topic TEXT, tags TEXT, version_tag TEXT, ttl_days INTEGER,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, verified_at TEXT,
  uses INTEGER NOT NULL DEFAULT 0, last_used_at TEXT);

CREATE TABLE IF NOT EXISTS code_snippets (
  id TEXT PRIMARY KEY, language TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
  code TEXT NOT NULL, code_hash TEXT NOT NULL, entrypoint TEXT, deps TEXT,
  license TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'hypothesis', trust REAL NOT NULL DEFAULT 0.3,
  trust_level INTEGER NOT NULL DEFAULT 0,               -- T0..T4 (06/03 §3)
  version_tag TEXT, task_signature TEXT, topics TEXT, symbols TEXT, source_kind TEXT, source_url TEXT,
  env TEXT, last_run_id TEXT, superseded_by TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, verified_at TEXT, uses INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS code_snippets_task ON code_snippets(task_signature, language);

CREATE TABLE IF NOT EXISTS snippet_tests (
  id TEXT PRIMARY KEY, snippet_id TEXT NOT NULL REFERENCES code_snippets(id) ON DELETE CASCADE,
  framework TEXT NOT NULL, test_code TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT, last_result TEXT, passed INTEGER, total INTEGER, runtime_ms INTEGER, env TEXT);

CREATE TABLE IF NOT EXISTS error_patterns (
  id TEXT PRIMARY KEY, lang TEXT NOT NULL, signature TEXT NOT NULL, example TEXT NOT NULL,
  causes TEXT NOT NULL DEFAULT '[]', fixes TEXT NOT NULL DEFAULT '[]',
  source_kind TEXT NOT NULL DEFAULT 'own-loop', license TEXT NOT NULL DEFAULT 'own',
  trust_level INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'hypothesis',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (lang, signature));

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, domain TEXT NOT NULL, title TEXT,
  fetched_at TEXT NOT NULL, content_hash TEXT, license TEXT, trust REAL NOT NULL, trust_reasons TEXT);

CREATE TABLE IF NOT EXISTS provenance (
  item_type TEXT NOT NULL, item_id TEXT NOT NULL, relation TEXT NOT NULL,
  ref_type TEXT NOT NULL, ref_id TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (item_type, item_id, relation, ref_type, ref_id));

CREATE TABLE IF NOT EXISTS episodes (
  id TEXT PRIMARY KEY, mode TEXT NOT NULL, origin TEXT NOT NULL, goal TEXT NOT NULL, outcome TEXT NOT NULL,
  level_start INTEGER, level_end INTEGER, llm_calls INTEGER, out_tokens INTEGER, wall_ms INTEGER,
  repair_rounds INTEGER, predicted_success REAL, started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE IF NOT EXISTS episode_steps (
  episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE, seq INTEGER NOT NULL,
  state TEXT NOT NULL, model TEXT, prompt_hash TEXT, out_tokens INTEGER, ms INTEGER,
  verdict TEXT, signature TEXT, PRIMARY KEY (episode_id, seq));
CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY, episode_id TEXT REFERENCES episodes(id), text TEXT NOT NULL, tags TEXT,
  success INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0, helped INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS snippet_use (
  snippet_id TEXT NOT NULL, task_id TEXT, outcome TEXT CHECK (outcome IN ('pass','fail')), at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS runs (                       -- one sandbox run (RunResult summary)
  id TEXT PRIMARY KEY, episode_id TEXT, task_id TEXT, lang TEXT, ok INTEGER NOT NULL,
  passed INTEGER, total INTEGER, duration_ms INTEGER, timed_out INTEGER, sandbox TEXT,
  digest TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS embeddings (
  item_type TEXT NOT NULL, item_id TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL,
  vec BLOB NOT NULL, text_hash TEXT NOT NULL, PRIMARY KEY (item_type, item_id, model));

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, priority INTEGER NOT NULL, state TEXT NOT NULL,
  payload TEXT NOT NULL, checkpoint TEXT, not_before TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(title, body, content='knowledge_items',
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS snippet_fts USING fts5(title, description, code, symbols,
  content='code_snippets', tokenize='unicode61 remove_diacritics 2');

CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_items BEGIN
  INSERT INTO knowledge_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body); END;
CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_items BEGIN
  INSERT INTO knowledge_fts(knowledge_fts, rowid, title, body) VALUES ('delete', old.rowid, old.title, old.body); END;
CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_items BEGIN
  INSERT INTO knowledge_fts(knowledge_fts, rowid, title, body) VALUES ('delete', old.rowid, old.title, old.body);
  INSERT INTO knowledge_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body); END;
CREATE TRIGGER IF NOT EXISTS snippet_ai AFTER INSERT ON code_snippets BEGIN
  INSERT INTO snippet_fts(rowid, title, description, code, symbols)
  VALUES (new.rowid, new.title, new.description, new.code, new.symbols); END;
CREATE TRIGGER IF NOT EXISTS snippet_ad AFTER DELETE ON code_snippets BEGIN
  INSERT INTO snippet_fts(snippet_fts, rowid, title, description, code, symbols)
  VALUES ('delete', old.rowid, old.title, old.description, old.code, old.symbols); END;
CREATE TRIGGER IF NOT EXISTS snippet_au AFTER UPDATE ON code_snippets BEGIN
  INSERT INTO snippet_fts(snippet_fts, rowid, title, description, code, symbols)
  VALUES ('delete', old.rowid, old.title, old.description, old.code, old.symbols);
  INSERT INTO snippet_fts(rowid, title, description, code, symbols)
  VALUES (new.rowid, new.title, new.description, new.code, new.symbols); END;
"""


class StoreError(ValueError):
    """A write the store's rules refuse (not green, no provenance, unknown license…)."""


@dataclass(frozen=True)
class Hit:
    item_type: str  # knowledge | snippet | error
    id: str
    title: str
    status: str
    trust: float
    score: float
    data: dict[str, Any]


# ── helpers ──────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _plain(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if hasattr(obj, "value") and obj.__class__.__module__ != "builtins" and not isinstance(obj, Mapping):
        return obj.value  # enums
    return obj


def _json(v: Any) -> str | None:
    return None if v is None else json.dumps(v, ensure_ascii=False, default=_plain)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def task_signature(*parts: str) -> str:
    """Normalized fingerprint of a task (cache key): whitespace-insensitive hash."""
    norm = "\n".join(re.sub(r"\s+", " ", p or "").strip() for p in parts)
    return "sig_" + _hash(norm)[:32]


def split_symbols(text: str) -> str:
    """`readFile` → `readFile read file`; `snake_case` → `snake_case snake case` (06/03 §2)."""
    out: list[str] = []
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        parts = [p for p in re.split(r"_|(?<=[a-z0-9])(?=[A-Z])", tok) if p]
        out.append(tok)
        if len(parts) > 1:
            out.extend(p.lower() for p in parts)
    return " ".join(dict.fromkeys(out))


def _fts_query(q: str) -> str:
    """User text → a safe FTS5 query (OR of quoted terms; no syntax injection)."""
    terms = [t for t in re.findall(r"\w+", q, flags=re.UNICODE) if len(t) >= 2][:16]
    return " OR ".join(f'"{t}"' for t in terms)


def _status(v: Any) -> str:
    s = str(_plain(v) or "hypothesis").lower()
    if s not in STATUSES:
        raise StoreError(f"ismeretlen státusz: {s}")
    return s


# ── the store ────────────────────────────────────────────────────────────────
class SqliteKnowledgeStore:
    """T0 store (`data/core.db`). `path=":memory:"` for tests."""

    def __init__(self, path: str | Path = ":memory:", *, names: Iterable[str] = ()) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        if self.path != ":memory:":
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=NORMAL")
        self._names = list(names)  # T1 (P1): the signed-in user's names, extra privacy matchers
        self.gate_calls = 0  # how many writes went through the privacy gate (tests read it)
        self.migrate()

    # ── schema ───────────────────────────────────────────────────────────────
    def migrate(self) -> None:
        """Idempotent; `schema_version` in `meta`."""
        self.db.executescript(_SCHEMA)
        self.db.execute(
            "INSERT INTO meta(key, value) VALUES ('schema_version', ?) ON CONFLICT(key) DO NOTHING", (str(SCHEMA_VERSION),)
        )

    def schema_version(self) -> int:
        row = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self.db.close()

    # ── the gate ─────────────────────────────────────────────────────────────
    def _gate(self, fields: dict[str, str | None], *, code_fields: Iterable[str] = ()) -> dict[str, str | None]:
        self.gate_calls += 1
        return privacy.guard(fields, code_fields=code_fields, names=self._names)

    def _provenance(self, item_type: str, item_id: str, prov: Iterable[Any], ts: str) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for p in prov:
            rel = str(_get(p, "relation", "") or "")
            rtype = str(_get(p, "ref_type", "") or "")
            rid = str(_get(p, "ref_id", "") or "")
            if not (rel and rtype and rid):
                raise StoreError("hiányos eredet-sor (relation, ref_type, ref_id kell)")
            g = self._gate({"ref_id": rid})
            rows.append((rel, rtype, str(g["ref_id"])))
        if not rows:
            raise StoreError("eredet nélküli elem nem tárolható")
        for rel, rtype, rid in rows:
            self.db.execute(
                "INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?)", (item_type, item_id, rel, rtype, rid, ts)
            )
        return rows

    @staticmethod
    def _only_model(rows: list[tuple[str, str, str]]) -> bool:
        return all(rtype == "model" for _, rtype, _ in rows)

    # ── knowledge items (KnowledgeStore Protocol) ─────────────────────────────
    async def put(self, item: Any, prov: list[Any]) -> str:
        """Insert a knowledge item; default status `hypothesis`."""
        ts = now_iso()
        status = _status(_get(item, "status", "hypothesis"))
        g = self._gate(
            {
                "title": str(_get(item, "title", "")),
                "body": str(_get(item, "body", "")),
                "topic": _get(item, "topic"),
                "tags": _json(_get(item, "tags")),
            },
            code_fields=("body",) if _get(item, "kind") in CODE_KINDS else (),
        )
        item_id = str(_get(item, "id") or f"k_{uuid.uuid4().hex[:16]}")
        self.db.execute("BEGIN")
        try:
            rows = self._provenance("knowledge", item_id, prov, ts)
            if status == "verified" and self._only_model(rows):
                raise StoreError("modell-kimenet egymagában nem lehet verified")
            self.db.execute(
                """INSERT INTO knowledge_items(id, kind, lang, title, body, status, verification, trust, topic, tags,
                   version_tag, ttl_days, created_at, updated_at, verified_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item_id,
                    str(_get(item, "kind", "fact")),
                    str(_get(item, "lang", "en")),
                    g["title"],
                    g["body"],
                    status,
                    _get(item, "verification"),
                    float(_get(item, "trust", 0.3)),
                    g["topic"],
                    g["tags"],
                    _get(item, "version_tag"),
                    _get(item, "ttl_days"),
                    ts,
                    ts,
                    ts if status == "verified" else None,
                ),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return item_id

    async def promote(self, item_id: str, v: Any) -> None:
        """→ `verified`. `v`: {"verification": "tests_passed|multi_source|…", "ref_type", "ref_id"}."""
        kind = str(_get(v, "kind", "") or _get(v, "verification", "") or "")
        rtype, rid = str(_get(v, "ref_type", "") or ""), str(_get(v, "ref_id", "") or "")
        if not kind or not rtype or not rid:
            raise StoreError("az előléptetéshez ellenőrzés és hivatkozás kell")
        if rtype == "model":
            raise StoreError("modell-kimenet egymagában nem lehet verified")
        ts = now_iso()
        table = self._table_of(item_id)
        self._provenance(table[1], item_id, [{"relation": "verified_by", "ref_type": rtype, "ref_id": rid}], ts)
        extra = ", verification=?" if table[0] == "knowledge_items" else ""
        params: tuple[Any, ...] = (ts, ts, kind, item_id) if extra else (ts, ts, item_id)
        self.db.execute(f"UPDATE {table[0]} SET status='verified', verified_at=?, updated_at=?{extra} WHERE id=?", params)

    async def demote(self, item_id: str, reason: str, *, status: str = "stale") -> None:
        if status not in {"stale", "contested", "refuted", "archived"}:
            raise StoreError(f"lefokozás csak stale/contested/refuted/archived lehet, nem {status}")
        table = self._table_of(item_id)
        g = self._gate({"reason": reason})
        ts = now_iso()
        self.db.execute(f"UPDATE {table[0]} SET status=?, updated_at=? WHERE id=?", (status, ts, item_id))
        self.db.execute(
            "INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?)",
            (table[1], item_id, "contradicted_by", "feedback", str(g["reason"])[:200], ts),
        )

    # ── P4 maintenance, no model (05/03 §5–6, 09 audit) ──────────────────────────────────────────
    HALF_LIFE_DAYS: ClassVar[dict[str, float]] = {"fact": 90.0, "definition": 90.0, "qa": 90.0, "api-note": 180.0, "source": 180.0,
                      "code": 365.0, "snippet": 365.0, "recipe": 365.0, "lesson": 365.0, "howto": 365.0}

    def mark_used(self, item_ids: Iterable[str]) -> None:
        """A signed-in caller used these items (recall, a green task): the usefulness clock restarts."""
        ts = now_iso()
        for iid in item_ids:  # snippets keep their own usage log (`snippet_use`, record_use)
            self.db.execute("UPDATE knowledge_items SET uses = uses + 1, last_used_at = ? WHERE id = ?", (ts, iid))

    def maintain(self, *, now: datetime | None = None) -> dict[str, int]:
        """Validity + usefulness clocks (05/03 §2, §6): TTL → stale; weak & unused ≥ 180 days → archived
        (kept, restorable); refuted > 30 days → deleted (provenance rows stay as history)."""
        now = now or datetime.now(UTC)
        out = {"stale": 0, "archived": 0, "deleted": 0}
        for r in self.db.execute("SELECT id, verified_at, ttl_days FROM knowledge_items WHERE status='verified' "
                                 "AND ttl_days IS NOT NULL AND verified_at IS NOT NULL").fetchall():
            if _days(now, r["verified_at"]) > float(r["ttl_days"]):
                self.db.execute("UPDATE knowledge_items SET status='stale', updated_at=? WHERE id=?", (now.isoformat(), r["id"]))
                out["stale"] += 1
        for r in self.db.execute("SELECT id, kind, uses, created_at, last_used_at FROM knowledge_items "
                                 "WHERE status IN ('verified','stale')").fetchall():
            idle = _days(now, r["last_used_at"] or r["created_at"])
            strength = min(1.0, (1 + int(r["uses"] or 0)) * 0.5 ** (idle / self.HALF_LIFE_DAYS.get(r["kind"], 90.0)))
            if idle >= 180 and strength < 0.1:
                self.db.execute("UPDATE knowledge_items SET status='archived', updated_at=? WHERE id=?", (now.isoformat(), r["id"]))
                self.db.execute("INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?)",
                                ("knowledge", r["id"], "archived_by", "feedback", f"unused {int(idle)}d", now.isoformat()))
                out["archived"] += 1
        old = [r["id"] for r in self.db.execute("SELECT id, updated_at FROM knowledge_items WHERE status='refuted'").fetchall()
               if _days(now, r["updated_at"]) > 30]
        for iid in old:
            self.db.execute("DELETE FROM knowledge_items WHERE id=?", (iid,))
        out["deleted"] = len(old)
        return out

    def dedupe(self, *, threshold: float = 0.82) -> list[tuple[str, str]]:
        """Exact (normalized hash) + near-text (Jaccard ≥ 0.82, as web/src/autolearn/dedup.ts) duplicates
        within the same kind · lang · version_tag (a different scope is never a duplicate, 05/03 §5).
        The higher-trust item stays; the other is archived with `merged_into` provenance and its sources
        are copied over. Returns (kept, merged) pairs."""
        groups: dict[tuple[Any, ...], list[sqlite3.Row]] = {}
        for r in self.db.execute("SELECT id, kind, lang, version_tag, title, body, trust, status FROM knowledge_items "
                                 "WHERE status IN ('verified','hypothesis','stale','contested')").fetchall():
            groups.setdefault((r["kind"], r["lang"], r["version_tag"] or ""), []).append(r)
        merged: list[tuple[str, str]] = []
        rank = {"verified": 3, "stale": 2, "contested": 1, "hypothesis": 0}
        ts = now_iso()
        for rows in groups.values():
            rows.sort(key=lambda r: (rank.get(r["status"], 0), float(r["trust"])), reverse=True)
            toks = [_tokens(f"{r['title']} {r['body']}") for r in rows]
            gone: set[int] = set()
            for i in range(len(rows)):
                if i in gone or not toks[i]:
                    continue
                for j in range(i + 1, len(rows)):
                    if j in gone or not toks[j]:
                        continue
                    a, b = toks[i], toks[j]
                    if len(a & b) / len(a | b) >= threshold:
                        keep, drop = rows[i]["id"], rows[j]["id"]
                        self.db.execute("UPDATE knowledge_items SET status='archived', updated_at=? WHERE id=?", (ts, drop))
                        self.db.execute("INSERT OR IGNORE INTO provenance SELECT 'knowledge', ?, relation, ref_type, ref_id, ? "
                                        "FROM provenance WHERE item_type='knowledge' AND item_id=?", (keep, ts, drop))
                        self.db.execute("INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?)",
                                        ("knowledge", drop, "merged_into", "feedback", keep, ts))
                        merged.append((keep, drop))
                        gone.add(j)
        return merged

    def audit_personal(self) -> list[str]:
        """09: 0 personal data in learned T0 items. Returns offending ids only (never the content)."""
        bad: list[str] = []
        for r in self.db.execute("SELECT id, kind, title, body FROM knowledge_items WHERE status != 'archived'").fetchall():
            kind = "code" if r["kind"] in CODE_KINDS else "text"
            if privacy.is_personal(r["title"] or "", self._names) or privacy.is_personal(r["body"] or "", self._names, kind=kind):
                bad.append(r["id"])
        for r in self.db.execute("SELECT id, title, description, code FROM code_snippets").fetchall():
            if privacy.is_personal(f"{r['title']}\n{r['description']}", self._names) or \
                    privacy.is_personal(r["code"] or "", self._names, kind="code"):
                bad.append(r["id"])
        for r in self.db.execute("SELECT id, text FROM lessons").fetchall() if _has_col(self.db, "lessons", "text") else []:
            if privacy.is_personal(r["text"] or "", self._names):
                bad.append(r["id"])
        return bad

    # ── jobs: the scheduler's durable queue (01/04 `jobs`; P5 /tasks, P4 background) ────────────
    JOB_STATES: ClassVar[frozenset[str]] = frozenset({"queued", "running", "paused", "interrupted", "done", "failed", "cancelled"})

    def create_job(self, kind: str, payload: dict[str, Any], *, priority: int = 1, text_fields: Iterable[str] = ()) -> str:
        """`text_fields` of the payload go through the privacy gate (a goal is user text)."""
        p = dict(payload)
        g = self._gate({k: p.get(k) for k in text_fields if isinstance(p.get(k), str)})
        p.update({k: v for k, v in g.items() if v is not None})
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        ts = now_iso()
        self.db.execute("INSERT INTO jobs(id, kind, priority, state, payload, checkpoint, not_before, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", (job_id, kind, priority, "queued", json.dumps(p, ensure_ascii=False),
                                                       None, None, ts, ts))
        return job_id

    def update_job(self, job_id: str, *, state: str | None = None, checkpoint: Any = None) -> None:
        if state is not None and state not in self.JOB_STATES:
            raise StoreError(f"ismeretlen feladat-állapot: {state}")
        sets, args = ["updated_at=?"], [now_iso()]
        if state is not None:
            sets.append("state=?")
            args.append(state)
        if checkpoint is not None:
            sets.append("checkpoint=?")
            args.append(json.dumps(checkpoint, ensure_ascii=False))
        self.db.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", (*args, job_id))

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        d["checkpoint"] = json.loads(d["checkpoint"]) if d.get("checkpoint") else None
        return d

    def list_jobs(self, *, kind: str | None = None, states: Iterable[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sql, args = "SELECT id FROM jobs WHERE 1=1", []
        if kind:
            sql += " AND kind=?"
            args.append(kind)
        st = list(states or [])
        if st:
            sql += f" AND state IN ({','.join('?' * len(st))})"
            args += st
        rows = self.db.execute(sql + " ORDER BY created_at DESC LIMIT ?", (*args, limit)).fetchall()
        return [j for j in (self.get_job(r[0]) for r in rows) if j]

    async def provenance(self, item_type: str, item_id: str) -> list[Provenance]:
        """Where an item came from (01/04 §2) — for `recall` sources and answers' citations."""
        kinds = ("snippet", "code") if item_type == "snippet" else (item_type,)
        rows = self.db.execute(
            f"SELECT relation, ref_type, ref_id FROM provenance WHERE item_id = ? AND item_type IN ({','.join('?' * len(kinds))})"
            " ORDER BY created_at",
            (item_id, *kinds),
        ).fetchall()
        return [Provenance(r[0], r[1], r[2]) for r in rows]

    async def put_source(self, url: str, *, title: str = "", domain: str = "", trust: float = 0.5,
                         trust_reasons: Any = None, license: str | None = None, content_hash: str | None = None) -> str:
        """Upsert one web source (01/04 `sources`); returns its id (`src_<hash>`), stable per URL.
        Knowledge items cite it as provenance `derived_from source <url>`."""
        url = url.strip()
        if not re.match(r"^https?://", url, re.I):
            raise StoreError("forrás csak http(s) URL lehet")
        g = self._gate({"url": url, "title": title or None, "reasons": _json(trust_reasons)}, code_fields=("url",))
        sid = "src_" + hashlib.sha1(url.encode()).hexdigest()[:16]
        dom = domain or (re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split("@")[-1].split(":")[0].lower())
        self.db.execute(
            """INSERT INTO sources(id, url, domain, title, fetched_at, content_hash, license, trust, trust_reasons)
               VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET title=excluded.title, fetched_at=excluded.fetched_at,
               content_hash=excluded.content_hash, license=COALESCE(excluded.license, sources.license),
               trust=excluded.trust, trust_reasons=excluded.trust_reasons""",
            (sid, g["url"], dom, g["title"], now_iso(), content_hash, license, max(0.0, min(1.0, float(trust))), g["reasons"]),
        )
        return sid

    def search_cache(self, **kw: Any) -> SqliteSearchCache:
        """The persistent counterpart of `research.search.SearchCache` (same get/put/key API)."""
        return SqliteSearchCache(self.db, **kw)

    async def adjust_trust(self, item_id: str, delta: float, *, ref_id: str) -> float:
        """Feedback (01/04 §5 A): trust ± delta, clamped to [0.05, 0.95]; recorded as provenance."""
        table = self._table_of(item_id)
        row = self.db.execute(f"SELECT trust FROM {table[0]} WHERE id=?", (item_id,)).fetchone()
        new = min(0.95, max(0.05, float(row[0]) + delta))
        ts = now_iso()
        self.db.execute(f"UPDATE {table[0]} SET trust=?, updated_at=? WHERE id=?", (new, ts, item_id))
        rel = "confirmed_by" if delta > 0 else "contradicted_by"
        self.db.execute("INSERT OR IGNORE INTO provenance VALUES (?,?,?,?,?,?)", (table[1], item_id, rel, "feedback", ref_id[:200], ts))
        return new

    def has_item(self, item_id: str) -> bool:
        try:
            self._table_of(item_id)
        except StoreError:
            return False
        return True

    def _table_of(self, item_id: str) -> tuple[str, str]:
        for table, kind in (("knowledge_items", "knowledge"), ("code_snippets", "snippet")):
            if self.db.execute(f"SELECT 1 FROM {table} WHERE id=?", (item_id,)).fetchone():
                return table, kind
        raise StoreError(f"nincs ilyen elem: {item_id}")

    # ── code snippets ────────────────────────────────────────────────────────
    async def put_snippet(
        self, snippet: Any, *, task_sig: str | None = None, episode_id: str | None = None, prov: list[Any] | None = None
    ) -> str:
        """Store a green solution (VerifiedSnippet, 06/03 §2). Refuses anything not green."""
        verification = _get(snippet, "verification") or {}
        if str(_get(verification, "status", "never")) != "pass":
            raise StoreError("csak zöld (lefuttatott, átment) megoldás kerülhet a tárba")
        source = _get(snippet, "source") or {}
        license_ = _get(source, "license", "own")
        if license_ in LICENSE_UNKNOWN:
            raise StoreError("ismeretlen licencű kód nem tárolható")
        tests = list(_get(snippet, "tests") or [])
        if not tests:
            raise StoreError("teszt nélküli snippet nem lehet verified")
        code = str(_get(snippet, "code", ""))
        g = self._gate(
            {
                "title": str(_get(snippet, "title", "")),
                "description": str(_get(snippet, "summary_hu", "") or _get(snippet, "description", "") or ""),
                "code": code,
            },
            code_fields=("code",),
        )
        test_rows = []
        for t in tests:
            tg = self._gate({"test_code": str(_get(t, "code", "") or _get(t, "test_code", ""))}, code_fields=("test_code",))
            test_rows.append((str(_get(t, "framework", "unittest")), str(tg["test_code"])))
        ts = now_iso()
        sid = str(_get(snippet, "id") or f"snip_{uuid.uuid4().hex[:16]}")
        run_id = _get(verification, "run_id") or _get(verification, "runId")
        level = int(_get(snippet, "trust", 2) or 2)
        level = max(2, min(level, 4))  # green tests → at least T2 (06/03 §3)
        self.db.execute("BEGIN")
        try:
            self.db.execute(
                """INSERT INTO code_snippets(id, language, title, description, code, code_hash, entrypoint, deps, license,
                   status, trust, trust_level, version_tag, task_signature, topics, symbols, source_kind, source_url, env,
                   last_run_id, created_at, updated_at, verified_at)
                   VALUES (?,?,?,?,?,?,?,?,?, 'verified', ?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sid,
                    str(_get(snippet, "lang", "") or _get(snippet, "language", "py")),
                    g["title"],
                    g["description"],
                    g["code"],
                    _hash(code),
                    _get(snippet, "entrypoint"),
                    _json(_get(_get(snippet, "env") or {}, "deps")),
                    str(license_),
                    level / 4,
                    level,
                    _get(snippet, "version_tag"),
                    task_sig or _get(snippet, "task_signature"),
                    _json(list(_get(snippet, "topics") or [])),
                    split_symbols(" ".join(list(_get(snippet, "symbols") or [])) + " " + code),
                    str(_get(source, "kind", "own-loop")),
                    _get(source, "url"),
                    _json(_get(snippet, "env")),
                    run_id,
                    ts,
                    ts,
                    ts,
                ),
            )
            for fw, tcode in test_rows:
                self.db.execute(
                    "INSERT INTO snippet_tests(id, snippet_id, framework, test_code, last_run_at, last_result) VALUES (?,?,?,?,?,?)",
                    (f"t_{uuid.uuid4().hex[:16]}", sid, fw, tcode, ts, "pass"),
                )
            rows = list(prov or [])
            if episode_id:
                rows.append({"relation": "verified_by", "ref_type": "episode", "ref_id": episode_id})
            if not rows and run_id:
                rows.append({"relation": "verified_by", "ref_type": "episode", "ref_id": str(run_id)})
            self._provenance("snippet", sid, rows, ts)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return sid

    async def find_snippet_for_task(self, task_sig: str, lang: str | None = None) -> dict[str, Any] | None:
        """Recall: a verified snippet for exactly this task signature (the 0-LLM-call path)."""
        sql = "SELECT * FROM code_snippets WHERE task_signature=? AND status='verified' AND superseded_by IS NULL"
        params: list[Any] = [task_sig]
        if lang:
            sql += " AND language=?"
            params.append(lang)
        row = self.db.execute(sql + " ORDER BY verified_at DESC LIMIT 1", params).fetchone()
        if row is None:
            return None
        self.db.execute("UPDATE code_snippets SET uses = uses + 1 WHERE id=?", (row["id"],))
        out = dict(row)
        out["tests"] = [
            dict(t) for t in self.db.execute("SELECT framework, test_code FROM snippet_tests WHERE snippet_id=?", (row["id"],))
        ]
        return out

    # ── error patterns (06/06 §7) ────────────────────────────────────────────
    async def put_error_pattern(self, pattern: Any) -> str:
        """Upsert by (lang, signature). Causes/fixes are merged; a fix that `worked` in the
        sandbox lifts trust to T2."""
        lang = str(_get(pattern, "lang", "any"))
        g = self._gate({"signature": str(_get(pattern, "signature", "")), "example": str(_get(pattern, "example", ""))})
        if not g["signature"]:
            raise StoreError("üres hibaaláírás")
        causes = [_plain(c) for c in _get(pattern, "causes") or []]
        fixes = [_plain(f) for f in _get(pattern, "fixes") or []]
        for c in causes:
            c["text_hu"] = self._gate({"text_hu": str(_get(c, "text_hu", ""))})["text_hu"]
        for f in fixes:
            f["text_hu"] = self._gate({"text_hu": str(_get(f, "text_hu", ""))})["text_hu"]
        ts = now_iso()
        row = self.db.execute("SELECT * FROM error_patterns WHERE lang=? AND signature=?", (lang, g["signature"])).fetchone()
        if row:
            causes = _merge(json.loads(row["causes"]), causes, counter="freq")
            fixes = _merge(json.loads(row["fixes"]), fixes, counter=None)
            pid = row["id"]
        else:
            pid = str(_get(pattern, "id") or f"err_{uuid.uuid4().hex[:16]}")
        worked = any(int(f.get("worked", 0) or 0) > 0 for f in fixes)
        level = 2 if worked else 0
        source = _get(pattern, "source") or {}
        self.db.execute(
            """INSERT INTO error_patterns(id, lang, signature, example, causes, fixes, source_kind, license, trust_level,
               status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(lang, signature) DO UPDATE SET causes=excluded.causes, fixes=excluded.fixes,
               trust_level=MAX(error_patterns.trust_level, excluded.trust_level), status=excluded.status,
               updated_at=excluded.updated_at""",
            (
                pid,
                lang,
                g["signature"],
                g["example"],
                _json(causes),
                _json(fixes),
                str(_get(source, "kind", "own-loop")),
                str(_get(source, "license", "own")),
                level,
                "verified" if worked else "hypothesis",
                ts,
                ts,
            ),
        )
        return pid

    async def find_error_pattern(self, signature: str, lang: str | None = None) -> dict[str, Any] | None:
        langs = [lang, "any"] if lang else ["any"]
        sql = f"SELECT * FROM error_patterns WHERE signature=? AND lang IN ({','.join('?' * len(langs))})"
        row = self.db.execute(sql + " ORDER BY trust_level DESC LIMIT 1", [signature, *langs]).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["causes"], d["fixes"] = json.loads(d["causes"]), json.loads(d["fixes"])
        return d

    # ── episodes & runs (append-only) ────────────────────────────────────────
    async def record_episode(self, ep: Any) -> str:
        g = self._gate({"goal": str(_get(ep, "goal", ""))})
        eid = str(_get(ep, "id") or f"ep_{uuid.uuid4().hex[:16]}")
        ts = now_iso()
        self.db.execute(
            """INSERT INTO episodes(id, mode, origin, goal, outcome, level_start, level_end, llm_calls, out_tokens,
               wall_ms, repair_rounds, predicted_success, started_at, ended_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid,
                str(_get(ep, "mode", "code")),
                str(_get(ep, "origin", "user")),
                g["goal"],
                str(_plain(_get(ep, "outcome", "DONE"))),
                _get(ep, "level_start"),
                _get(ep, "level_end"),
                _get(ep, "llm_calls"),
                _get(ep, "out_tokens"),
                _get(ep, "wall_ms"),
                _get(ep, "repair_rounds"),
                _get(ep, "predicted_success"),
                str(_get(ep, "started_at") or ts),
                _get(ep, "ended_at") or ts,
            ),
        )
        for i, step in enumerate(_get(ep, "steps") or []):
            await self.append_step(eid, step, seq=int(_get(step, "seq", i)))
        return eid

    async def append_step(self, episode_id: str, step: Any, *, seq: int) -> None:
        g = self._gate({"verdict": _get(step, "verdict"), "signature": _get(step, "signature")})
        self.db.execute(
            "INSERT INTO episode_steps VALUES (?,?,?,?,?,?,?,?,?)",
            (
                episode_id,
                seq,
                str(_get(step, "state", "")),
                _get(step, "model"),
                _get(step, "prompt_hash"),
                _get(step, "out_tokens"),
                _get(step, "ms"),
                g["verdict"],
                g["signature"],
            ),
        )

    async def record_run(self, run: Any, *, run_id: str | None = None, episode_id: str | None = None, task_id: str | None = None, digest: str | None = None) -> str:
        """Summary of one RunResult (06/04 §7). The raw output stays in the run journal."""
        g = self._gate({"digest": digest})
        rid = str(run_id or _get(run, "run_id") or _get(run, "runId") or f"run_{uuid.uuid4().hex[:16]}")
        self.db.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                rid,
                episode_id,
                task_id,
                _get(run, "lang"),
                1 if _get(run, "ok", False) else 0,
                _get(run, "passed"),
                _get(run, "total"),
                _get(run, "duration_ms") or _get(run, "durationMs"),
                1 if _get(run, "timed_out", False) or _get(run, "timedOut", False) else 0,
                _get(run, "sandbox", "S0"),
                g["digest"],
                now_iso(),
            ),
        )
        return rid

    async def add_lesson(self, text: str, *, episode_id: str | None, success: bool, tags: list[str] | None = None) -> str:
        g = self._gate({"text": text, "tags": _json(tags)})
        lid = f"les_{uuid.uuid4().hex[:16]}"
        self.db.execute(
            "INSERT INTO lessons(id, episode_id, text, tags, success) VALUES (?,?,?,?,?)",
            (lid, episode_id, g["text"], g["tags"], 1 if success else 0),
        )
        return lid

    # ── search (FTS5; vectors come in P1) ────────────────────────────────────
    async def search(self, q: str, *, kinds: set[str] | None = None, scope: Any = None, k: int = 8) -> list[Hit]:
        """Lexical, diacritics-insensitive search. `kinds`: {"knowledge", "snippet"}."""
        del scope  # T0 only in P0; T1 per-user DB in P1
        fq = _fts_query(q)
        if not fq:
            return []
        kinds = kinds or {"knowledge", "snippet"}
        hits: list[Hit] = []
        if "knowledge" in kinds:
            for r in self.db.execute(
                """SELECT k.*, bm25(knowledge_fts) AS rank FROM knowledge_fts JOIN knowledge_items k ON k.rowid = knowledge_fts.rowid
                   WHERE knowledge_fts MATCH ? AND k.status NOT IN ('refuted','archived') ORDER BY rank LIMIT 50""",
                (fq,),
            ):
                hits.append(_hit("knowledge", r))
        if "snippet" in kinds:
            for r in self.db.execute(
                """SELECT s.*, bm25(snippet_fts) AS rank FROM snippet_fts JOIN code_snippets s ON s.rowid = snippet_fts.rowid
                   WHERE snippet_fts MATCH ? AND s.status NOT IN ('refuted','archived') ORDER BY rank LIMIT 50""",
                (fq,),
            ):
                hits.append(_hit("snippet", r))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    async def recall(self, q: str, *, k: int = 5, verified_only: bool = True, lang: str | None = None) -> list[dict[str, Any]]:
        """T0 recall for callers' own prompts (01/03 §4 `/recall`): top-k with provenance.
        Default: only `verified` items — a hypothesis is never handed out as knowledge.
        A topic stored in several languages (seed definitions hu+en) comes back once, in `lang` if given."""
        hits = await self.search(q, k=50)
        if verified_only:
            hits = [h for h in hits if h.status == "verified"]
        if lang:
            hits.sort(key=lambda h: h.data.get("lang") != lang)  # stable: preferred language first
        seen: set[str] = set()
        picked = []
        for h in hits:
            key = f"{h.item_type}:{h.data.get('kind')}:{h.data.get('topic')}" if h.data.get("kind") == "definition" else h.id
            if key not in seen:
                seen.add(key)
                picked.append(h)
        if lang:
            picked.sort(key=lambda h: h.score, reverse=True)
        out: list[dict[str, Any]] = []
        for h in picked[:k]:
            d = h.data
            body = d.get("body") or d.get("summary_hu") or ""
            src_type = "knowledge" if h.item_type == "knowledge" else h.item_type
            sources = [{"relation": r[0], "ref_type": r[1], "ref_id": r[2]} for r in self.db.execute(
                "SELECT relation, ref_type, ref_id FROM provenance WHERE item_type IN (?, ?) AND item_id = ?",
                (src_type, "snippet" if h.item_type == "snippet" else src_type, h.id))]
            item: dict[str, Any] = {"type": h.item_type, "id": h.id, "title": h.title, "body": body,
                                    "status": h.status, "trust": h.trust, "score": round(h.score, 4), "sources": sources}
            if h.item_type == "snippet":
                item.update(lang=d.get("lang"), code=d.get("code"))
            out.append(item)
        return out

    def counts(self) -> dict[str, int]:
        tables = ("knowledge_items", "code_snippets", "error_patterns", "episodes", "runs", "lessons", "provenance")
        return {t: int(self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in tables}


class SqliteCodeMemory(SqliteKnowledgeStore):
    """`contracts.CodeMemory` (P0): solutions + error knowledge, typed in and out."""

    async def find_solution(self, task_signature: str, lang: str) -> VerifiedSnippet | None:
        row = await self.find_snippet_for_task(task_signature, lang)
        return None if row is None else _row_to_snippet(row)

    async def save_solution(self, snippet: VerifiedSnippet, *, task_signature: str, prov: list[Provenance]) -> str:
        return await self.put_snippet(snippet, task_sig=task_signature, prov=prov)

    async def record_use(self, snippet_id: str, task_id: str, ok: bool) -> None:
        self.db.execute("INSERT INTO snippet_use VALUES (?,?,?,?)", (snippet_id, task_id, "pass" if ok else "fail", now_iso()))

    async def find_error(self, signature: str, lang: str) -> ErrorPattern | None:
        d = await self.find_error_pattern(signature, lang)
        if d is None:
            return None
        return ErrorPattern(
            id=d["id"],
            lang=d["lang"],
            signature=d["signature"],
            example=d["example"],
            causes=[ErrorCause(text_hu=c.get("text_hu", ""), freq=int(c.get("freq", 1))) for c in d["causes"]],
            fixes=[
                ErrorFix(text_hu=f.get("text_hu", ""), snippet_id=f.get("snippet_id"), worked=int(f.get("worked", 0)), failed=int(f.get("failed", 0)))
                for f in d["fixes"]
            ],
            source=PatternSource(kind=d["source_kind"], license=d["license"]),
            trust=d["trust_level"],
        )

    async def save_error(self, pattern: ErrorPattern) -> str:
        return await self.put_error_pattern(pattern)


class SqliteSearchCache:
    """Search hit lists in SQLite (03/01 §7), the same contract as `research.search.SearchCache`:
    volatile topic 1 h, stable 7 days, empty result (negative) 1 h. Survives restarts, so the web is
    not asked again for the same question after a reboot. Hits are public search results (no gate)."""

    def __init__(self, db: sqlite3.Connection, *, max_entries: int = 2000, clock: Any = time.time) -> None:
        self.db = db
        self.max_entries = max_entries
        self.clock = clock

    @staticmethod
    def key(query: str) -> str:
        return " ".join(query.lower().split())

    def get(self, query: str, *, allow_stale: bool = False) -> list[Any] | None:
        from .research.types import SearchResult

        row = self.db.execute("SELECT hits, stored_at, ttl_s FROM search_cache WHERE key = ?", (self.key(query),)).fetchone()
        if row is None or (not allow_stale and self.clock() - row[1] > row[2]):
            return None
        return [SearchResult(**h) for h in json.loads(row[0])]

    def put(self, query: str, hits: list[Any]) -> None:
        from .research.search import ttl_days_for_query

        ttl = 3600.0 if not hits or ttl_days_for_query(query) <= 3 else 7 * 86400.0
        data = json.dumps([{"title": h.title, "url": h.url, "snippet": h.snippet, "provider": h.provider} for h in hits],
                          ensure_ascii=False)
        self.db.execute("INSERT INTO search_cache VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET hits=excluded.hits, "
                        "stored_at=excluded.stored_at, ttl_s=excluded.ttl_s", (self.key(query), data, self.clock(), ttl))
        n = self.db.execute("SELECT COUNT(*) FROM search_cache").fetchone()[0]
        if n > self.max_entries:
            self.db.execute("DELETE FROM search_cache WHERE key IN (SELECT key FROM search_cache ORDER BY stored_at LIMIT ?)",
                            (n - self.max_entries,))


def _row_to_snippet(row: dict[str, Any]) -> VerifiedSnippet:
    env = json.loads(row["env"]) if row.get("env") else {}
    return VerifiedSnippet(
        id=row["id"],
        lang=row["language"],
        title=row["title"],
        summary_hu=row["description"],
        code=row["code"],
        tests=[SnippetTest(framework=t["framework"], code=t["test_code"]) for t in row.get("tests", [])],
        env=SnippetEnv(**{k: v for k, v in (env or {}).items() if k in {"node", "python", "typescript", "deps"}}),
        topics=json.loads(row["topics"] or "[]"),
        symbols=[],
        source=SnippetSource(kind=row["source_kind"] or "own-loop", license=row["license"], url=row["source_url"]),
        trust=row["trust_level"],
        verification=SnippetVerification(status="pass", run_id=row["last_run_id"], at=row["verified_at"]),
        usage=SnippetUsage(retrieved=row["uses"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        superseded_by=row["superseded_by"],
    )


def _hit(item_type: str, r: sqlite3.Row) -> Hit:
    d = dict(r)
    status = d.get("status", "hypothesis")
    rel = -float(d.pop("rank", 0.0))  # bm25: lower is better → negate
    score = (rel if rel > 0 else 1e-6) * float(d.get("trust", 0.3)) * STATUS_WEIGHT.get(status, 0.0)
    return Hit(item_type=item_type, id=d["id"], title=d.get("title", ""), status=status, trust=float(d.get("trust", 0.3)), score=score, data=d)


def _merge(old: list[dict[str, Any]], new: list[dict[str, Any]], *, counter: str | None) -> list[dict[str, Any]]:
    by_text = {str(o.get("text_hu", "")): dict(o) for o in old}
    for n in new:
        key = str(n.get("text_hu", ""))
        if key in by_text:
            cur = by_text[key]
            if counter:
                cur[counter] = int(cur.get(counter, 0) or 0) + int(n.get(counter, 1) or 1)
            else:
                for c in ("worked", "failed"):
                    cur[c] = int(cur.get(c, 0) or 0) + int(n.get(c, 0) or 0)
                if n.get("snippet_id"):
                    cur["snippet_id"] = n["snippet_id"]
        else:
            by_text[key] = dict(n)
    return list(by_text.values())


def open_store(path: str | Path | None = None) -> SqliteCodeMemory:
    """The default T0 store at `config.db_path` (implements contracts.CodeMemory)."""
    from .config import load_config

    return SqliteCodeMemory(path or load_config().db_path)


def _days(now: datetime, iso: str | None) -> float:
    if not iso:
        return 0.0
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return 0.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return max(0.0, (now - t).total_seconds() / 86400.0)


_WORD = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD.findall(privacy.fold(text)) if len(w) > 1)


def _has_col(db: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in db.execute(f"PRAGMA table_info({table})"))
