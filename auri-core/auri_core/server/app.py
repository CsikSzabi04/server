"""FastAPI app: `/core/v1/*` (P1). Spec: 01/03 §4 (API), §6 (tiers), §7 (migration), §8 (done-when).

Security (01/03 §8): Host must be our loopback host:port (DNS rebinding) → else 403; a browser
Origin must be in `cfg.allowed_origins` → else 403; `Authorization: Bearer <token>` → else 401.
The token is generated at first start into `data/core.token` (git-ignored, never logged); local
clients (AuriGPT dev proxy, Jarvis) read it from there.

Tiers (01/03 §6): `X-Auri-User` verified → T0 + the user's own T1; otherwise **guest**: reads T0
only, writes nothing — no T1 file, no run journal, no feedback.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from ..config import Config, load_config
from ..contracts import GUEST as GUEST_SCOPE
from ..contracts import AskEvent, Scope
from ..contracts import AskRequest as CoreAskRequest
from ..privacy import PrivacyError
from ..scheduler import USER_PRIORITIES, Scheduler, get_scheduler, rank_name
from ..store import StoreError
from .identity import Identity, UserStores, Verifier
from .tasks import TaskManager

API = "/core/v1"
TOKEN_FILE = "core.token"
FEEDBACK_DELTA = 0.05


class AskBody(BaseModel):
    text: str = Field(max_length=8000)
    mode: Literal["chat", "code", "research"] = "chat"
    lang: Literal["hu", "en"] | None = None
    context: list[str] = Field(default_factory=list, max_length=20)
    allow_web: bool = False
    allow_cloud: bool = False


class RecallBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=20)
    lang: Literal["hu", "en"] | None = None


class LearnBody(BaseModel):
    kind: Literal["qa", "fact", "snippet", "doc"] = "qa"
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=8000)
    lang: str = Field(default="hu", max_length=12)
    source: str = Field(default="", max_length=500)


class FeedbackBody(BaseModel):
    item_id: str = Field(min_length=1, max_length=120)
    verdict: Literal["good", "bad", "fix"]
    correction: str = Field(default="", max_length=4000)


class BrainStateBody(BaseModel):
    state: dict[str, Any]


class TaskBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    mode: Literal["project", "research"] = "project"
    lang: Literal["hu", "en"] | None = None
    allow_web: bool = False


class BackgroundBody(BaseModel):
    no_study: bool  # the manual "ma ne tanulj" switch (05/02 §2)


class ActivityBody(BaseModel):
    source: Literal["jarvis", "web"] = "web"
    state: Literal["active", "idle"] = "active"


class ReadOnlyStore:
    """A guest's view of T0 (01/03 §6): read methods only — no `put`, so nothing downstream
    (research, solve) can write for a guest. `hasattr(store, "put")` is False on purpose."""

    _READ = frozenset({"search", "recall", "find_solution", "find_error", "find_snippet_for_task",
                       "find_error_pattern", "provenance", "has_item", "counts"})

    def __init__(self, store: Any) -> None:
        self._store = store

    def __getattr__(self, name: str) -> Any:
        if name in self._READ:
            return getattr(self._store, name)
        raise AttributeError(name)


def scope_of(ident: Identity) -> Scope:
    return GUEST_SCOPE if ident.user_id is None else Scope("user", ident.user_id)


def load_or_create_token(data_dir: Path) -> str:
    path = data_dir / TOKEN_FILE
    with contextlib.suppress(OSError):
        tok = path.read_text("utf-8").strip()
        if len(tok) >= 32:
            return tok
    data_dir.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(32)
    path.write_text(tok, "utf-8")
    return tok


def _err(status: int, kind: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"kind": kind, "message": message}}, status_code=status)


def sse(ev: AskEvent) -> bytes:
    return f"event: {ev.type}\ndata: {json.dumps(ev.data, ensure_ascii=False)}\n\n".encode()


def create_app(
    cfg: Config | None = None,
    *,
    token: str | None = None,
    llm: Any = None,
    scheduler: Scheduler | Any = None,
    sandbox: Any = None,
    store: Any = None,
    verifier: Verifier | None = None,
    task_run: Any = None,
    start_background: bool = True,
) -> FastAPI:
    """Dependencies are injectable for tests (fakes); defaults are the real ones, made lazily."""
    cfg = cfg or load_config()
    token = token or load_or_create_token(cfg.data_dir)
    sched = scheduler or get_scheduler()
    hosts = {f"{h}:{cfg.server_port}" for h in ("127.0.0.1", "localhost", cfg.server_host)}
    origins = set(cfg.allowed_origins)
    deps: dict[str, Any] = {"llm": llm, "sandbox": sandbox, "store": store}
    ver = verifier or Verifier(cfg)
    users = UserStores(cfg.users_dir)

    def _llm() -> Any:
        if deps["llm"] is None:
            from ..llm import OllamaClient

            deps["llm"] = OllamaClient(cfg)
        return deps["llm"]

    def _store() -> Any:
        if deps["store"] is None:
            from ..store import open_store

            deps["store"] = open_store(cfg.db_path)
        return deps["store"]

    def _search() -> Any:
        """Keyless web search (P2) with the SQLite hit cache (survives restarts)."""
        if deps.get("search") is None:
            from ..research import DuckDuckGoHtml, ResilientSearch, Searxng

            st = _store()
            cache = st.search_cache() if hasattr(st, "search_cache") else None
            deps["search"] = ResilientSearch([DuckDuckGoHtml(), Searxng()], cache=cache)
        return deps["search"]

    def _watcher() -> Any:
        if deps.get("watcher") is None:
            from ..idle import IdleWatcher, maintenance_job

            w = IdleWatcher(_store(), sched, mode=cfg.background, flag_dir=cfg.data_dir)  # type: ignore[arg-type]
            w.register("maintenance", maintenance_job, light=True)
            deps["watcher"] = w
        return deps["watcher"]

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        bg = None
        if cfg.background != "off" and start_background:
            bg = asyncio.create_task(_watcher().run())
        yield
        if bg is not None:
            bg.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await bg
        client = deps["llm"]
        if client is not None and hasattr(client, "aclose"):
            await client.aclose()
        st = deps["store"]
        if st is not None and hasattr(st, "close"):
            st.close()
        if deps.get("tasks") is not None:
            await deps["tasks"].aclose()
        users.close()
        await ver.aclose()

    app = FastAPI(title="Auri Core", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    def _cors(resp: Response, origin: str | None) -> Response:
        if origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
        return resp

    @app.middleware("http")
    async def guard(request: Request, call_next: Any) -> Response:
        if request.headers.get("host", "") not in hosts:
            return _err(403, "forbidden_host", "ismeretlen Host fejléc")
        origin = request.headers.get("origin")
        if origin is not None and origin.rstrip("/") not in origins:
            return _err(403, "forbidden_origin", "ez az oldal nem hívhatja a Core-t")
        if request.method == "OPTIONS" and origin:  # CORS preflight: no token on it by design
            resp = Response(status_code=204)
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Auri-User"
            resp.headers["Access-Control-Max-Age"] = "600"
            return _cors(resp, origin)
        auth = request.headers.get("authorization", "")
        if not (auth.startswith("Bearer ") and secrets.compare_digest(auth[7:].strip(), token)):
            return _cors(_err(401, "unauthorized", "hiányzó vagy rossz token"), origin)
        return _cors(await call_next(request), origin)

    async def _ident(request: Request) -> Identity:
        """Checked lazily (only endpoints that need it): /health must stay instant."""
        if not hasattr(request.state, "ident"):
            request.state.ident = await ver.identify(request.headers.get("x-auri-user"))
        return request.state.ident

    async def _signed_in(request: Request) -> Identity | JSONResponse:
        ident = await _ident(request)
        if ident.guest:
            return _err(403, "guest_read_only", "vendégként csak olvasni lehet — jelentkezz be")
        return ident

    def _sandbox() -> Any:
        if deps["sandbox"] is None:
            from ..sandbox import create_sandbox

            deps["sandbox"] = create_sandbox()
        return deps["sandbox"]

    def _cloud() -> Any:
        """AI-3's CloudClient, only when the user turned the cloud on (08/03); ask() still needs consent."""
        if cfg.cloud_mode == "off":
            return None
        if deps.get("cloud") is None:
            from ..cloud.client import CloudClient

            deps["cloud"] = CloudClient(cfg, _store())
        return deps["cloud"]

    def _tasks() -> TaskManager:
        if deps.get("tasks") is None:
            from ..ask import ask as core_ask
            from ..contracts import AskRequest as Req
            from ..contracts import Priority

            def run(payload: dict[str, Any]) -> AsyncIterator[AskEvent]:
                project = payload.get("mode") == "project"
                req = Req(text=payload["text"], mode="code" if project else "research", lang=payload.get("lang"),
                          allow_web=bool(payload.get("allow_web")), plan=project, priority=Priority.TASK)
                return core_ask(req, llm=_llm(), scheduler=sched, sandbox=_sandbox() if project else deps["sandbox"],
                                store=_store(), runs_dir=cfg.runs_dir, scope=Scope("user", payload.get("user_id")),
                                search=_search() if payload.get("allow_web") else None,
                                resume_run_id=payload.get("resume_run_id"))  # step-level resume (P5)

            deps["tasks"] = TaskManager(_store(), task_run or run)
        return deps["tasks"]

    @app.get(f"{API}/health")
    async def health() -> dict[str, Any]:
        ollama: dict[str, Any] = {"ok": False, "loaded": []}
        with contextlib.suppress(Exception):
            loaded = await _llm().loaded_models()
            ollama = {"ok": True, "loaded": [m.get("name") or m.get("model") for m in loaded]}
        holder = getattr(sched, "holder", None)
        return {"ok": True, "ollama": ollama, "identity": ver.configured,
                "lane": {"busy": holder is not None, "prio": rank_name(holder.prio) if holder else None,
                         "queue": getattr(sched, "queue_len", 0), "user_active": sched.user_active()}}

    @app.get(f"{API}/background")
    async def background() -> dict[str, Any]:
        return _watcher().describe()

    @app.post(f"{API}/background", response_model=None)
    async def background_set(body: BackgroundBody, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        flag = cfg.data_dir / "no_study"
        if body.no_study:
            cfg.data_dir.mkdir(parents=True, exist_ok=True)
            flag.write_text("1", "utf-8")
        else:
            flag.unlink(missing_ok=True)
        return _watcher().describe()

    @app.get(f"{API}/cloud/audit", response_model=None)
    async def cloud_audit(request: Request) -> dict[str, Any] | JSONResponse:
        """08/03 §4: what left the machine (already masked), last 30 days. Keys are never stored."""
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        rows = _store().db.execute("SELECT at, provider, model, purpose, chars, redactions, text, ok FROM cloud_audit "
                                   "ORDER BY at DESC LIMIT 100").fetchall()
        return {"mode": cfg.cloud_mode, "items": [dict(r) for r in rows]}

    @app.get(f"{API}/whoami")
    async def whoami(request: Request) -> dict[str, Any]:
        ident = await _ident(request)
        return {"guest": ident.guest, "tiers": ["T0"] if ident.guest else ["T0", "T1"]}

    @app.post(f"{API}/activity")
    async def activity(body: ActivityBody) -> dict[str, Any]:
        released = False
        if body.state == "active":
            if hasattr(sched, "note_user_activity"):
                sched.note_user_activity()
            holder = getattr(sched, "holder", None)
            if holder is not None and rank_name(holder.prio) not in USER_PRIORITIES:
                holder.preempt.set()  # background work yields the lane at once (01/03 §5)
                released = True
        return {"ok": True, "preempted": released}

    @app.post(f"{API}/recall")
    async def recall(body: RecallBody, request: Request) -> dict[str, Any]:
        from ..contracts import RecallRequest
        from ..recall import recall as mind_recall

        ident = await _ident(request)
        block = await mind_recall(RecallRequest(body.query, k=body.k, lang=body.lang), store=ReadOnlyStore(_store()),
                                  scope=scope_of(ident))
        items = [{**i, "tier": "T0"} for i in await _store().recall(body.query, k=body.k, lang=body.lang)]
        if not ident.guest and hasattr(_store(), "mark_used"):  # usefulness clock (05/03 §6); guests write nothing
            _store().mark_used([i["id"] for i in items if i["type"] == "knowledge"])
        t1 = users.get(await _ident(request), create=False)
        if t1 is not None:  # own T1: hypotheses too (they are the user's own notes), marked as such
            items += [{**i, "tier": "T1"} for i in await t1.recall(body.query, k=body.k, verified_only=False, lang=body.lang)]
            items.sort(key=lambda i: i["score"], reverse=True)
        return {"items": items[: body.k], "prompt_block": block.prompt_block, "withheld": block.withheld}

    @app.get(f"{API}/stats")
    async def stats(request: Request) -> dict[str, Any]:
        out: dict[str, Any] = {"phase": "P1", "counts": _store().counts()}
        with contextlib.suppress(Exception):  # P6: the measured routing table (empty until bench data exists)
            from ..router import load_router

            r = load_router(cfg)
            out["router"] = r.describe() if hasattr(r, "describe") else []
        t1 = users.get(await _ident(request), create=False)
        if t1 is not None:
            out["own"] = t1.counts()
        return out

    @app.post(f"{API}/learn", response_model=None)
    async def learn(body: LearnBody, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        t1 = users.get(ident)
        assert t1 is not None
        kind = {"snippet": "code"}.get(body.kind, body.kind)
        prov = [{"relation": "derived_from", "ref_type": "source" if body.source else "feedback",
                 "ref_id": body.source or "user"}]
        try:  # always a hypothesis (01/04 §4), in the user's own T1; T0 only after verification
            item_id = await t1.put({"kind": kind, "lang": body.lang, "title": body.title, "body": body.body,
                                    "status": "hypothesis", "trust": 0.3}, prov)
        except PrivacyError as e:
            return _err(422, "privacy", str(e))
        return {"ok": True, "id": item_id, "tier": "T1", "status": "hypothesis"}

    @app.post(f"{API}/feedback", response_model=None)
    async def feedback(body: FeedbackBody, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        t1 = users.get(ident, create=False)
        ref = "user-feedback"
        try:
            if t1 is not None and t1.has_item(body.item_id):  # own note: the user decides
                if body.verdict == "good":
                    await t1.promote(body.item_id, {"verification": "user_confirmed", "ref_type": "feedback", "ref_id": ref})
                else:
                    await t1.demote(body.item_id, "a felhasználó javította", status="refuted")
                tier, store = "T1", t1
            elif _store().has_item(body.item_id):  # shared T0: one user only nudges trust / contests it
                store, tier = _store(), "T0"
                delta = FEEDBACK_DELTA if body.verdict == "good" else -FEEDBACK_DELTA
                await store.adjust_trust(body.item_id, delta, ref_id=ref)
                if body.verdict == "fix":
                    await store.demote(body.item_id, "felhasználói javítás érkezett", status="contested")
            else:
                return _err(404, "not_found", "nincs ilyen elem")
            new_id = None
            if body.verdict == "fix" and body.correction.strip():
                own = users.get(ident)
                assert own is not None
                new_id = await own.put({"kind": "fact", "title": f"javítás: {body.item_id}", "body": body.correction,
                                        "status": "hypothesis", "trust": 0.3},
                                       [{"relation": "corrects", "ref_type": "feedback", "ref_id": body.item_id}])
        except PrivacyError as e:
            return _err(422, "privacy", str(e))
        except StoreError as e:
            return _err(409, "store", str(e))
        return {"ok": True, "tier": tier, "correction_id": new_id}

    @app.post(f"{API}/import/brain-state", response_model=None)
    async def import_brain_state(body: BrainStateBody, request: Request) -> dict[str, Any] | JSONResponse:
        """01/03 §7.3: the signed-in user's old web BRAIN → own T1 as hypotheses. Only the Q→A
        pairs; each one through the privacy gate again (personal ones are dropped, not stored)."""
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        qa = body.state.get("qa")
        if not isinstance(qa, list):
            return {"ok": True, "added": 0, "skipped": 0, "dropped": 0}
        t1 = users.get(ident)
        assert t1 is not None
        added = skipped = dropped = 0
        for i, p in enumerate(qa[:5000]):
            q, a = (str(p.get("q", "")).strip(), str(p.get("a", "")).strip()) if isinstance(p, dict) else ("", "")
            if not q or not a or len(q) > 500 or len(a) > 4000:
                skipped += 1
                continue
            try:
                await t1.put({"kind": "qa", "lang": "hu", "title": q, "body": a, "status": "hypothesis", "trust": 0.3},
                             [{"relation": "derived_from", "ref_type": "feedback", "ref_id": f"brain_state#qa{i}"}])
                added += 1
            except PrivacyError:
                dropped += 1
        return {"ok": True, "added": added, "skipped": skipped, "dropped": dropped}

    @app.delete(f"{API}/account", response_model=None)
    async def delete_account(request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        return {"ok": True, "deleted": users.delete(ident)}

    # ── long tasks (P5): signed-in only, each user sees only their own ────────────────────────
    @app.post(f"{API}/tasks", response_model=None)
    async def task_start(body: TaskBody, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        assert ident.user_id is not None
        try:
            job_id = _tasks().start({"text": body.text, "mode": body.mode, "lang": body.lang, "allow_web": body.allow_web},
                                    ident.user_id)
        except PrivacyError as e:
            return _err(422, "privacy", str(e))
        return {"ok": True, "id": job_id}

    @app.get(f"{API}/tasks", response_model=None)
    async def task_list(request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        assert ident.user_id is not None
        return {"tasks": _tasks().list(ident.user_id)}

    @app.get(f"{API}/tasks/{{job_id}}", response_model=None)
    async def task_get(job_id: str, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        assert ident.user_id is not None
        t = _tasks().get(job_id, ident.user_id)
        return t if t else _err(404, "not_found", "nincs ilyen feladat")

    @app.get(f"{API}/tasks/{{job_id}}/events", response_model=None)
    async def task_events(job_id: str, request: Request, start: int = 0) -> StreamingResponse | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        assert ident.user_id is not None
        tm = _tasks()
        if tm.get(job_id, ident.user_id) is None:
            return _err(404, "not_found", "nincs ilyen feladat")

        async def stream() -> AsyncIterator[bytes]:
            async with contextlib.aclosing(tm.follow(job_id, max(0, start))) as evs:
                async for ev in evs:
                    if await request.is_disconnected():
                        break  # only the viewer leaves; the task keeps running
                    yield sse(AskEvent(ev["type"], ev["data"]))

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    @app.post(f"{API}/tasks/{{job_id}}/{{action}}", response_model=None)
    async def task_control(job_id: str, action: str, request: Request) -> dict[str, Any] | JSONResponse:
        ident = await _signed_in(request)
        if isinstance(ident, JSONResponse):
            return ident
        assert ident.user_id is not None
        tm = _tasks()
        if action == "resume":
            ok = tm.resume(job_id, ident.user_id)
        elif action in ("cancel", "pause"):
            ok = await tm.stop(job_id, ident.user_id, as_state="cancelled" if action == "cancel" else "paused")
        else:
            return _err(404, "not_found", "ismeretlen művelet (cancel / pause / resume)")
        return {"ok": ok, "task": tm.get(job_id, ident.user_id)}

    @app.post(f"{API}/ask")
    async def ask(body: AskBody, request: Request) -> StreamingResponse:
        from ..ask import ask as core_ask

        ident = await _ident(request)
        guest = ident.guest
        req = CoreAskRequest(text=body.text, mode=body.mode, lang=body.lang, context=tuple(body.context),
                             allow_web=body.allow_web, allow_cloud=body.allow_cloud)

        async def stream() -> AsyncIterator[bytes]:
            # guest: RAM only — no run journal, no store (01/03 §6)
            st = _store()
            gen = core_ask(req, llm=_llm(), scheduler=sched, sandbox=deps["sandbox"],
                           store=ReadOnlyStore(st) if guest else st, runs_dir=None if guest else cfg.runs_dir,
                           scope=scope_of(ident), search=_search() if body.allow_web else None,
                           cloud=None if guest else _cloud())
            async with contextlib.aclosing(gen) as events:
                async for ev in events:
                    if await request.is_disconnected():
                        break  # aclosing → model stream closed, lane released
                    yield sse(ev)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app


def main_serve(argv: list[str]) -> int:
    """`python -m auri_core serve` — local only (NK21), started by hand."""
    del argv
    import uvicorn

    cfg = load_config()
    if cfg.server_host not in ("127.0.0.1", "localhost", "::1"):
        print(f"A Core csak helyben futhat (AURI_CORE_HOST={cfg.server_host} nem engedélyezett).")
        return 2
    app = create_app(cfg)
    who = "bejelentkezés: Supabase" if Verifier(cfg).configured else "mindenki vendég (nincs AURI_CORE_SUPABASE_URL)"
    print(f"Auri Core: http://{cfg.server_host}:{cfg.server_port}{API} — token: {cfg.data_dir / TOKEN_FILE} — {who}")
    uvicorn.run(app, host=cfg.server_host, port=cfg.server_port, log_level="warning", access_log=False)
    return 0
