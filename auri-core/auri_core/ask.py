"""auri_core.ask — the loop as an async event stream (P1, owner: AI-1). AI-3's POST /ask calls `ask()`.

Events (01/03 §4): route → step* → delta* → verify* → done | error. Rules kept from P0:
- every model call runs inside `scheduler.lease()`; a preempted lease stops the stream (error "paused");
- `done.verified` is True only after a green test run (hallucination guard); free-text code is unverified;
- error messages are Hungarian and never contain paths, tokens or the user's text.
Closing the generator (client gone) closes the model stream and cancels a running solve().
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

from .contracts import (
    BUDGETS,
    GUEST,
    SOLUTION_FILENAME,
    AskEvent,
    AskRequest,
    Cancelled,
    CodeMemory,
    CodeTask,
    EndState,
    Failure,
    LLMClient,
    Outcome,
    Priority,
    Sandbox,
    Scheduler,
    Scope,
    SolveOptions,
)
from .l4 import CloudGate, CloudLLM, CloudRefused, make_gate, offer_text, shown_by
from .lang import answer_lang, detect_lang
from .router import SimpleRouter, load_router
from .solve import Journal, _b36, load_prompts, solve

MAX_TEXT = 8000
MAX_CONTEXT_CHARS = 4000
CHAT_TEMPERATURE = 0.2
LANG_NAME = {"en": {"hu": "Hungarian", "en": "English"}, "hu": {"hu": "magyarul", "en": "angolul"}}
FENCE = {"py": "python", "ts": "ts", "js": "js", "sql": "sql"}
SOLUTION_LANG = {".py": "py", ".ts": "ts", ".js": "js", ".sql": "sql"}


def _ev(type_: str, **data: Any) -> AskEvent:
    return AskEvent(type_, data)  # type: ignore[arg-type]


def _error(kind: str, message: str) -> AskEvent:
    return _ev("error", kind=kind, message=message)


def _safe_message(e: BaseException) -> str:
    """Hungarian, secret-free: only a provider's own user_message, else the exception type."""
    return getattr(e, "user_message", None) or f"belső hiba ({type(e).__name__})"


def _user_content(text: str, context: tuple[str, ...]) -> str:
    ctx = "\n---\n".join(c for c in context if c.strip())[:MAX_CONTEXT_CHARS]
    return f"<context>\n{ctx}\n</context>\n\n{text}" if ctx else text


async def ask(
    req: AskRequest,
    *,
    llm: LLMClient,
    scheduler: Scheduler,
    sandbox: Sandbox | None = None,
    store: CodeMemory | None = None,
    router: SimpleRouter | None = None,
    runs_dir: Path | None = None,
    prompt_lang: str = "en",
    scope: Scope = GUEST,
    roles: Any = None,  # roles.RolesConfig; enabled → free-text code gets TESZTELO tests + the loop (P3)
    search: Any = None,  # research.SearchAdapter; None + allow_web → the keyless default adapters (P2)
    fetcher: Any = None,  # research fetcher; None + allow_web → SafeFetcher (SSRF-guarded)
    cloud: Any = None,  # cloud.CloudClient (AI-3); used only at L4 and only with consent (l4.py)
    resume_run_id: str | None = None,  # /tasks: continue a project run from its last checkpoint
) -> AsyncIterator[AskEvent]:
    text = req.text.strip()
    if not text and req.task is None:
        yield _error("bad_request", "üres kérés")
        return
    if len(req.text) > MAX_TEXT:
        yield _error("bad_request", f"túl hosszú kérés (legfeljebb {MAX_TEXT} karakter)")
        return
    if req.mode == "study":
        yield _error("not_available", "a háttértanulás (study) nem kérésre fut, hanem tétlen időben (P4)")
        return
    if req.mode == "research" and not req.allow_web:
        yield _error("not_available", "a kutatáshoz webes engedély kell (allow_web)")
        return
    if req.mode == "code" and (req.task is not None or req.plan) and sandbox is None:
        yield _error("not_available", "nincs sandbox, így a kódot nem tudom ellenőrizni")
        return
    web = _Web(search, fetcher, store) if req.allow_web else None
    gate = make_gate(cloud, req, scope)
    common = {"llm": llm, "scheduler": scheduler, "router": router, "runs_dir": runs_dir, "prompt_lang": prompt_lang}
    if req.mode == "research":
        inner = _ask_research(req, text, store=store, scope=scope, web=web, **common)  # type: ignore[arg-type]
    elif req.mode == "code" and req.task is not None:
        inner = _ask_task(req, req.task, sandbox=sandbox, store=store, cloud=gate, **common)  # type: ignore[arg-type]
    elif req.mode == "code" and req.plan:
        inner = _ask_project(req, text, sandbox=sandbox, store=store, scope=scope, web=web,  # type: ignore[arg-type]
                             resume_run_id=resume_run_id, **common)
    elif req.mode == "code" and sandbox is not None and getattr(roles, "enabled", False):
        inner = _ask_spec(req, text, roles=roles, sandbox=sandbox, store=store, cloud=gate, **common)
    else:
        inner = _ask_chat(req, text, llm=llm, scheduler=scheduler, router=router, runs_dir=runs_dir,
                          prompt_lang=prompt_lang, cloud=gate)
    async with contextlib.aclosing(inner) as events:  # client gone → close the inner stream at once
        async for e in events:
            yield e


async def _ask_chat(req: AskRequest, text: str, *, llm: LLMClient, scheduler: Scheduler,
                    router: SimpleRouter | None, runs_dir: Path | None, prompt_lang: str,
                    cloud: CloudGate | None = None) -> AsyncIterator[AskEvent]:
    """chat, or code without tests: one streamed model call; the answer is never 'verified'.
    Ollama down + the router says L4 → the cloud once (with consent), else an honest error + offer."""
    lang = answer_lang(text, req.lang)
    rt = router or load_router()
    model, why = rt.chat_model()
    run_id = f"ask_{_b36(int(time.time()))}{secrets.token_hex(2)}"
    journal = Journal(runs_dir / run_id / "journal.jsonl" if runs_dir else None)
    prompts = load_prompts(prompt_lang, kind="chat")
    section = "code_system" if req.mode == "code" else "system"
    messages = [
        {"role": "system", "content": prompts.render(section, answer_language=LANG_NAME[prompt_lang][lang])},
        {"role": "user", "content": _user_content(text, req.context)},
    ]
    journal.write("start", mode=req.mode, lang=lang, detected=detect_lang(text), model=model, route=why,
                  prompt_ver=prompts.version, chars=len(text), context_items=len(req.context))
    yield _ev("route", level=2, model=model, mode=req.mode, lang=lang)
    t0 = time.monotonic()
    yield _ev("step", state="ACT", ms=0)
    out_chars, stats, done_reason = 0, None, None
    try:
        async with scheduler.lease(req.priority, model) as lease:
            if lease.preempt.is_set():
                raise Cancelled("preempted before the call")
            kw: dict[str, Any] = {"num_predict": BUDGETS["chat"].out_tokens, "temperature": CHAT_TEMPERATURE}
            stream = getattr(llm, "chat_stream", None)
            if stream is None:  # a plain LLMClient: one delta
                reply = await llm.chat(lease, messages, **kw)
                stats = reply.stats
                out_chars = len(reply.text)
                yield _ev("delta", text=reply.text)
            else:
                async with contextlib.aclosing(stream(lease, messages, **kw)) as chunks:
                    async for ch in chunks:
                        if getattr(ch, "stats", None) is not None:
                            stats = ch.stats
                        if ch.content:
                            out_chars += len(ch.content)
                            yield _ev("delta", text=ch.content)
                        if lease.preempt.is_set():  # voice turn waiting: yield the lane now
                            raise Cancelled("preempted while streaming")
    except Cancelled:
        journal.write("paused", out_chars=out_chars)
        yield _error("paused", "megszakítva: magasabb prioritású kérés (pl. hang) kapta meg a modellt")
        return
    except Exception as e:  # Ollama down, model missing, … — never the user's fault
        journal.write("infra_error", kind=type(e).__name__)
        nxt = (rt.escalate(2, Failure("llm_unavailable"), interactive=req.priority >= Priority.CHAT, kind="chat",
                           lang=lang) if out_chars == 0 and cloud is not None and hasattr(rt, "pick") else None)
        if nxt == 4 and cloud is not None and cloud.configured:
            async with contextlib.aclosing(_cloud_chat(messages, cloud, journal, run_id, _safe_message(e), req, lang)) as evs:
                async for ev in evs:
                    yield ev
            return
        yield _error("infra", _safe_message(e))
        return
    done_reason = getattr(stats, "done_reason", None)
    ms = int((time.monotonic() - t0) * 1000)
    journal.write("done", out_chars=out_chars, ms=ms, done_reason=done_reason,
                  out_tokens=getattr(stats, "eval_tokens", None))
    yield _ev("done", outcome="partial" if done_reason == "length" else "answered", episode_id=run_id,
              sources=[], verified=False, ms=ms)


async def _cloud_chat(messages: list[dict[str, str]], gate: CloudGate, journal: Journal, run_id: str, local_error: str,
                      req: AskRequest, lang: str) -> AsyncIterator[AskEvent]:
    """L4 for chat: one cloud call; the answer is a hypothesis, marked with who answered (08/03 §1, §7)."""
    if not gate.usable:
        journal.write("cloud_offer", live=gate.live)
        yield AskEvent("error", {"kind": "infra", "message": f"{local_error}. {offer_text()}", "cloud_offer": gate.live})
        return
    t0 = time.monotonic()
    llm = CloudLLM(gate, purpose="chat", max_calls=1)
    try:
        reply = await llm.chat(None, messages)
    except CloudRefused as r:
        journal.write("cloud", ok=False, kind=r.kind)
        yield _error("infra", f"{local_error}; felhő: {r.user_message}")
        return
    except Exception as e:  # a bug in the client — no details
        journal.write("cloud", ok=False, kind=type(e).__name__)
        yield _error("infra", f"{local_error}; felhő: belső hiba ({type(e).__name__})")
        return
    prov = llm.provenance or "cloud"
    journal.write("cloud", ok=True, provenance=prov, out_chars=len(reply.text))
    yield _ev("route", level=4, model=prov, mode=req.mode, lang=lang)
    yield _ev("delta", text=reply.text)
    yield _ev("delta", text=f"\n\n_(Ezt a felhő válaszolta: {shown_by(prov)} — nem ellenőrzött feltevés.)_\n")
    yield _ev("done", outcome="answered", episode_id=run_id, sources=[], verified=False,
              provenance=prov, level=4, ms=int((time.monotonic() - t0) * 1000))


class _Web:
    """The web adapters of one session (P2). Real keyless adapters only when the caller gave none."""

    def __init__(self, search: Any, fetcher: Any, store: Any = None) -> None:
        if search is None or fetcher is None:
            from .research import DuckDuckGoHtml, ResilientSearch, SafeFetcher, Searxng

            # AI-3's SQLite cache survives restarts: the web is not asked again for the same query
            cache = store.search_cache() if hasattr(store, "search_cache") else None
            search = search or ResilientSearch([DuckDuckGoHtml(), Searxng()], cache=cache)
            fetcher = fetcher or SafeFetcher()
        self.search, self.fetcher = search, fetcher


async def _pump(start: Callable[[Callable[[str, dict[str, Any]], None]], Awaitable[Any]],
                mapper: Callable[[str, dict[str, Any]], list[AskEvent]], holder: list[Any]) -> AsyncIterator[AskEvent]:
    """Run `start(on_event)` as a task; stream its mapped events; put its result into `holder`.
    Closing this generator (client gone) cancels the task (leases are released by their context managers)."""
    q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
    job = asyncio.create_task(start(lambda ev, d: q.put_nowait((ev, d))))
    job.add_done_callback(lambda _t: q.put_nowait(None))
    try:
        while (item := await q.get()) is not None:
            for e in mapper(*item):
                yield e
        holder.append(job.result())
    finally:
        if not job.done():
            job.cancel()


async def _ask_task(req: AskRequest, task: CodeTask, *, llm: LLMClient, scheduler: Scheduler, sandbox: Sandbox,
                    store: CodeMemory | None, router: SimpleRouter | None, runs_dir: Path | None, prompt_lang: str,
                    visible: dict[str, str] | None = None, learn: bool | None = None, emit_route: bool = True,
                    extra_done: dict[str, Any] | None = None, cloud: CloudGate | None = None) -> AsyncIterator[AskEvent]:
    """code with a CodeTask: the P0 loop; its journal events become step/verify events."""
    lang = answer_lang(req.text or task.prompt_hu, req.lang)
    opts = SolveOptions(prompt_lang=prompt_lang, priority=req.priority, learn=learn)  # type: ignore[arg-type]
    st: dict[str, Any] = {"state": "ACT", "t": time.monotonic(), "routed": not emit_route}

    def mapper(ev: str, d: dict[str, Any]) -> list[AskEvent]:
        if ev == "start":
            if st["routed"]:
                return [_ev("step", state="ACT", ms=0, model=d.get("model", ""))]
            st["routed"] = True
            return [_ev("route", level=2, model=d.get("model", ""), mode="code", lang=lang)]
        if ev == "recall":
            return [_ev("step", state="RECALL", ms=0)]
        if ev == "llm":
            return [_ev("step", state=st["state"], ms=d.get("ms", 0))]
        if ev == "verify":
            return [_ev("verify", ok=d.get("status") == "pass", tests={"passed": d.get("passed", 0),
                        "failed": d.get("failed", 0)}, signature=d.get("signature"))]
        if ev == "repair":
            st["state"] = "REPAIR"
        elif ev == "escalate":
            st["state"] = "ACT"
            return [_ev("step", state="ESCALATE", ms=0, to=d.get("to"), reason=d.get("reason"))]
        elif ev == "cloud_offer":
            st["cloud_offer"] = bool(d.get("live"))
        elif ev == "cloud":
            return [_ev("step", state="CLOUD", ms=0, ok=d.get("ok"), provenance=d.get("provenance"))]
        elif ev == "store" and st["state"] != "STORE":
            st["state"] = "STORE"
            return [_ev("step", state="STORE", ms=int((time.monotonic() - st["t"]) * 1000))]
        return []

    holder: list[Outcome] = []
    try:
        async with contextlib.aclosing(_pump(
            lambda on: solve(task, llm=llm, sandbox=sandbox, store=store, scheduler=scheduler, opts=opts,
                             visible=visible, runs_dir=runs_dir, router=router, on_event=on, cloud=cloud),
            mapper, holder)) as events:
            async for e in events:
                yield e
    except Exception as e:  # solve() returns Outcomes; this is only for a bug in it
        yield _error("infra", _safe_message(e))
        return
    out = holder[0]
    code = out.files.get(SOLUTION_FILENAME[task.lang])
    if code:
        yield _ev("delta", text=f"```{FENCE[task.lang]}\n{code.rstrip()}\n```\n")
    if out.kind != "pass" and out.reason_hu:
        yield _ev("delta", text=f"Nem lett zöld: {out.reason_hu}\n")
    from_cloud = out.model.startswith("cloud:")
    if from_cloud:
        yield _ev("delta", text=f"_(A kódot a felhő írta: {shown_by(out.model)}; a helyi sandbox "
                                f"{'zöldre' if out.kind == 'pass' else 'nem zöldre'} futtatta a teszteket.)_\n")
    if st.get("cloud_offer"):
        yield _ev("delta", text=offer_text() + "\n")
    if out.end_state == EndState.PAUSED:
        yield _error("paused", out.reason_hu or "megszakítva")
        return
    extra = dict(extra_done or {})
    if from_cloud:
        extra.update(provenance=out.model, level=4)
    if st.get("cloud_offer"):
        extra["cloud_offer"] = True
    yield _ev("done", outcome=out.kind, episode_id=out.run_id,
              sources=[out.snippet_id] if out.from_memory and out.snippet_id else [],
              verified=out.kind == "pass", from_memory=out.from_memory, rounds=out.rounds, reason=out.reason_hu,
              files=out.files, ms=out.wall_ms, **extra)


def _code_lang(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(typescript|ts)\b", t):
        return "ts"
    if re.search(r"\b(javascript|js|node)\b", t):
        return "js"
    return "py"


async def _ask_spec(req: AskRequest, text: str, *, roles: Any, llm: LLMClient, scheduler: Scheduler,
                    sandbox: Sandbox, store: CodeMemory | None, router: SimpleRouter | None, runs_dir: Path | None,
                    prompt_lang: str, cloud: CloudGate | None = None) -> AsyncIterator[AskEvent]:
    """Free-text code (P3): TESZTELO writes tests from the request (never from code), then the P0 loop.
    Own tests are never learned (learn=False). Unusable tests → the plain, unverified chat answer."""
    from .roles import RoleSession, SpecTestsRejected, spec_to_task

    lang = answer_lang(text, req.lang)
    model = (router or load_router()).chat_model()[0]
    yield _ev("route", level=2, model=model, mode="code", lang=lang)
    yield _ev("step", state="TESZTELO", ms=0)
    session = RoleSession(llm, scheduler, cfg=roles, model=model, priority=req.priority)
    try:
        spec = await spec_to_task(session, text, lang=_code_lang(text), sandbox=sandbox)  # type: ignore[arg-type]
    except Cancelled:
        yield _error("paused", "megszakítva: magasabb prioritású kérés kapta meg a modellt")
        return
    except SpecTestsRejected as e:
        yield _ev("step", state="TESZTELO_REJECTED", ms=0, reason=e.reason_hu)
        async with contextlib.aclosing(_ask_chat(req, text, llm=llm, scheduler=scheduler, router=router,
                                                 runs_dir=runs_dir, prompt_lang=prompt_lang, cloud=cloud)) as events:
            async for ev in events:
                if ev.type != "route":
                    yield ev
        return
    except Exception as e:
        yield _error("infra", _safe_message(e))
        return
    yield _ev("step", state="TESZTELO_DONE", ms=0, covers=list(spec.covers))
    async with contextlib.aclosing(_ask_task(
            req, spec.task, llm=llm, scheduler=scheduler, sandbox=sandbox, store=store, router=router,
            runs_dir=runs_dir, prompt_lang=prompt_lang, visible=spec.visible, learn=False, emit_route=False,
            extra_done={"tests_source": spec.tests_source, "tests": spec.visible}, cloud=cloud)) as events:
        async for e in events:
            yield e


def _research_mapper(ev: str, d: dict[str, Any]) -> list[AskEvent]:
    if ev in ("recall", "search", "read", "extract", "verify", "store"):
        return [_ev("step", state=f"RESEARCH:{ev}", ms=int(d.get("ms", 0) or 0))]
    return []


async def _ask_research(req: AskRequest, text: str, *, llm: LLMClient, scheduler: Scheduler, store: Any,
                        scope: Scope, web: _Web, router: SimpleRouter | None, runs_dir: Path | None,
                        prompt_lang: str) -> AsyncIterator[AskEvent]:
    """research (P2): search → read → extract → >= 2 independent sources → store; the answer says how sure."""
    from .research import research

    lang = answer_lang(text, req.lang)
    yield _ev("route", level=2, model=(router or load_router()).chat_model()[0], mode="research", lang=lang)
    holder: list[Any] = []
    try:
        async with contextlib.aclosing(_pump(
            lambda on: research(text, llm=llm, scheduler=scheduler, store=store, search=web.search,
                                fetcher=web.fetcher, scope=scope, lang=lang, on_event=on, prompt_lang=prompt_lang,
                                priority=req.priority, runs_dir=runs_dir, router=router),
            _research_mapper, holder)) as events:
            async for e in events:
                yield e
    except Exception as e:  # research() never raises by contract; a bug only
        yield _error("infra", _safe_message(e))
        return
    res = holder[0]
    if res.answer:
        yield _ev("delta", text=res.answer)
    elif res.reason_hu:
        yield _ev("delta", text=f"Nem találtam megbízható választ: {res.reason_hu}\n")
    if res.end_state == EndState.PAUSED:
        yield _error("paused", res.reason_hu or "megszakítva")
        return
    yield _ev("done", outcome=res.kind, episode_id=res.episode_id, sources=[s.url for s in res.sources],
              verified=any(c.status == "verified" for c in res.claims), from_memory=res.from_memory,
              web_checked=res.web_checked, stored=len(res.stored), reason=res.reason_hu, ms=res.wall_ms)


class _SkipPlanning(Exception):
    pass


_RUN_ID = re.compile(r"proj_[a-z0-9]{4,32}")


def _resumable(runs_dir: Path | None, run_id: str | None) -> str | None:
    """The run id when its journal holds a plan (only our own id shape: no path tricks)."""
    if not run_id or runs_dir is None or not _RUN_ID.fullmatch(run_id):
        return None
    from .planner.executor import read_journal

    try:
        events = read_journal(runs_dir / run_id)
    except (OSError, ValueError):
        return None
    has_plan = any(e.get("type") in ("plan.created", "plan.replanned") for e in events)
    return run_id if has_plan and any(e.get("type") == "run.start" for e in events) else None


OWN_TESTS_NOTE = {
    "hu": "Figyelem: a teszteket is én írtam a célból, így a „kész” csak azt jelenti, hogy a saját tesztjeim "
          "zöldek. Nézd át őket, mielőtt élesben használod.\n",
    "en": "Note: I wrote the tests too, from the goal, so “done” only means my own tests are green. "
          "Review them before you rely on it.\n",
}


def _project_mapper(ev: str, d: dict[str, Any]) -> list[AskEvent]:
    if ev == "task.start":
        return [_ev("step", state="TASK", ms=0, task=d.get("task"), kind=d.get("kind"), title=d.get("title"),
                    attempt=d.get("attempt"))]
    if ev == "task.done":
        return [_ev("verify", ok=True, task=d.get("task"), tests=None, signature=None)]
    if ev in ("task.failed", "task.retry"):
        return [_ev("verify", ok=False, task=d.get("task"), tests=None,
                    signature=str(d.get("digest") or "").strip().split("\n")[0][:200] or None)]
    if ev in ("plan.replanned", "milestone.done", "gate.failed", "run.paused"):
        return [_ev("step", state=ev.upper().replace(".", "_"), ms=0)]
    return []


async def _ask_project(req: AskRequest, text: str, *, llm: LLMClient, scheduler: Scheduler, sandbox: Sandbox,
                       store: Any, scope: Scope, web: _Web | None, router: SimpleRouter | None,
                       runs_dir: Path | None, prompt_lang: str,
                       resume_run_id: str | None = None) -> AsyncIterator[AskEvent]:
    """A multi-step goal (P5): recipe or plan → validated DAG → steps with real checks → re-plan → recipe.
    `resume_run_id` (from /tasks): the journal gives the plan, the finished steps and the last checkpoint;
    the run continues at the step boundary. Not resumable (no journal / no plan yet) → a fresh run."""
    from .planner import RecipeBook, execute, make_plan, make_replanner
    from .project import make_step_runner

    lang = answer_lang(text, req.lang)
    rt = router or load_router()
    model = rt.chat_model()[0]
    recipes = RecipeBook(store, scope=scope)
    resumed = _resumable(runs_dir, resume_run_id)
    run_id = resumed or f"proj_{_b36(int(time.time()))}{secrets.token_hex(2)}"
    yield _ev("route", level=2, model=model, mode="code", lang=lang, run_id=run_id)
    if resume_run_id and not resumed:
        yield _ev("step", state="RESUME_FAILED", ms=0, reason="a korábbi futás nem folytatható, újrakezdem")
    plan = None
    if resumed:
        yield _ev("step", state="RESUME", ms=0, run_id=run_id)
    else:
        yield _ev("step", state="PLAN", ms=0)
    try:
        if resumed:
            raise _SkipPlanning
        planned = await make_plan(text, llm=llm, scheduler=scheduler, router=rt, recipes=recipes,
                                  prompt_lang=prompt_lang, priority=req.priority)
    except _SkipPlanning:
        planned = None
    except Cancelled:
        yield _error("paused", "megszakítva: magasabb prioritású kérés kapta meg a modellt")
        return
    except Exception as e:
        yield _error("infra", _safe_message(e))
        return
    if planned is None:
        pass
    elif not planned.ok or planned.plan is None:
        reason = planned.reason_hu or "; ".join(planned.errors[:3]) or "nem sikerült érvényes tervet készíteni"
        yield _ev("delta", text=f"Nem tudtam tervet készíteni: {reason}\n")
        yield _ev("done", outcome="give_up", episode_id=run_id, sources=[], verified=False, reason=reason)
        return
    else:
        plan = planned.plan
        yield _ev("step", state="PLAN_READY", ms=0, tasks=len(plan.tasks), created_by=planned.created_by,
                  run_id=run_id)

    async def research_fn(question: str) -> str | None:
        from .research import research

        assert web is not None
        r = await research(question, llm=llm, scheduler=scheduler, store=store, search=web.search,
                           fetcher=web.fetcher, scope=scope, lang=lang, prompt_lang=prompt_lang,
                           priority=req.priority, router=rt)
        return r.answer if any(c.status == "verified" for c in r.claims) else None

    runner = make_step_runner(llm=llm, scheduler=scheduler, sandbox=sandbox, model=model, prompt_lang=prompt_lang,
                              priority=req.priority, research=research_fn if web is not None else None)
    replanner = make_replanner(llm=llm, scheduler=scheduler, router=rt, prompt_lang=prompt_lang,
                               priority=req.priority)
    holder: list[Any] = []
    try:
        async with contextlib.aclosing(_pump(
            lambda on: execute(plan, runner=runner, replanner=replanner, run_id=run_id, on_event=on,
                               run_dir=runs_dir / run_id if runs_dir else None, resume=resumed is not None),
            _project_mapper, holder)) as events:
            async for e in events:
                yield e
    except Cancelled:
        yield _error("paused", "megszakítva: magasabb prioritású kérés kapta meg a modellt")
        return
    except Exception as e:
        yield _error("infra", _safe_message(e))
        return
    out = holder[0]
    for path, body in sorted(out.files.items()):
        fence = FENCE.get(SOLUTION_LANG.get(Path(path).suffix, ""), "")
        yield _ev("delta", text=f"`{path}`\n```{fence}\n{body.rstrip()}\n```\n")
    if out.report_hu:
        yield _ev("delta", text=out.report_hu.rstrip() + "\n")
    if out.state == "paused":
        yield _error("paused", out.report_hu or "megszakítva")
        return
    recipe_id = None
    # the run wrote its own tests: "done" = green against tests written from the goal, not against the user's
    # (e5 2026-11-24: E5-04 was "done" with its own tests green and the hidden acceptance tests red)
    own_tests = any(t.kind == "test" for t in out.plan.tasks)
    if out.state == "done":
        recipe_id = await recipes.save(text, out.plan, run_id=run_id, model=model, lang=lang)
        if own_tests:
            yield _ev("delta", text=OWN_TESTS_NOTE.get(lang, OWN_TESTS_NOTE["en"]))
    yield _ev("done", outcome={"done": "pass", "waiting_user": "ask_user"}.get(out.state, "give_up"),
              episode_id=run_id, sources=[], verified=out.state == "done", question=out.question,
              files=out.files, replans=out.replans, recipe=recipe_id, ms=out.wall_ms,
              tests_source="own" if own_tests else "given")
