"""research() — question → (store?) → search → read → extract → verify quotes → corroborate → store.

Spec: thinking/03-web-szorfozes/01–04. Rules kept:
- the store answers first when it already holds VERIFIED knowledge for the question (no web);
- the query is redacted; a question that stays personal after redaction never leaves the machine;
- page text is data (`<web_adat>`), quotes are checked by code, never trusted from the model;
- only claims backed by ≥ 2 INDEPENDENT sources (different registrable domain, not a copy), at least
  one of class A/B, none suspicious/noindex, are stored — as `verified` / `multi_source`, with
  `derived_from` provenance per source (03/03 §3, ai_prompts.md P2). Everything else is only answered,
  with an honest certainty label;
- every model call inside `scheduler.lease()`; budget = BUDGETS["research"]; Hungarian give-up text.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import privacy
from ..contracts import (
    ABORTED,
    BUDGETS,
    GUEST,
    Cancelled,
    EndState,
    KnowledgeItem,
    Priority,
    PrivacyRejected,
    Provenance,
    Scope,
    chat_or_abort,
)
from ..lang import answer_lang, detect_lang
from ..router import SimpleRouter
from ..solve import Journal, _b36, load_prompts
from .extract import EXTRACT_SCHEMA, RawClaim, code_ok, parse_claims, quote_ok, relevant_text, web_block
from .query import expand_query, merge_results
from .text import extract_keywords, fold, keyword_overlap, norm_quote, text_similar
from .trust import (
    TrustOverrides,
    independent_count,
    registrable_domain,
    source_class,
    trust_score,
    ttl_days_for_query,
)
from .types import (
    Claim,
    Fetcher,
    PageDoc,
    ResearchResult,
    SearchAdapter,
    SearchResult,
    SourceInfo,
    SourceRef,
)

OUT_TOKENS = 1200  # one extraction reply (≤ 6 claims with quotes); within BUDGETS["research"].out_tokens
TEMPERATURE = 0.0
_LANG_NAME = {"en": {"hu": "Hungarian", "en": "English"}, "hu": {"hu": "magyarul", "en": "angolul"}}
_KIND_TO_ITEM = {"fact": "fact", "api": "fact", "concept": "concept", "snippet": "howto", "fix": "howto"}
_LABELS = {
    "hu": {
        "verified": "két független forrás szerint", "probable": "egy forrás szerint",
        "probable_many": "{n} forrás szerint, de egyik sem elsődleges",
        "hypothesis": "bizonytalan — nem tudtam ellenőrizni", "memory": "ellenőrzött tudás a tárból",
        "none": "Nem találtam a weben ellenőrizhető választ erre a kérdésre.",
        "offline": "Most nem tudtam a neten ellenőrizni.",
    },
    "en": {
        "verified": "according to two independent sources", "probable": "according to one source",
        "probable_many": "according to {n} sources, none of them primary",
        "hypothesis": "uncertain — I could not verify it", "memory": "verified knowledge from my store",
        "none": "I found no answer on the web that I could verify.",
        "offline": "I could not check this on the web right now.",
    },
}
Listener = Callable[[str, dict[str, Any]], None]


class _Budget:
    def __init__(self) -> None:
        b = BUDGETS["research"]
        self.limits = b
        self.t0 = time.monotonic()
        self.llm_calls = self.searches = self.pages = self.tokens_out = 0

    def over_time(self) -> bool:
        return time.monotonic() - self.t0 > self.limits.wall_s

    @property
    def wall_ms(self) -> int:
        return int((time.monotonic() - self.t0) * 1000)


def _field(h: Any, *names: str) -> Any:
    data = getattr(h, "data", None) or {}
    for n in names:
        v = getattr(h, n, None)
        if v is None:
            v = data.get(n)
        if v not in (None, ""):
            return v
    return None


def _ref_id(url: str) -> str:
    """Provenance ref for a source URL. URLs with long digit runs trip the privacy gate (a question id
    looks like a phone number) → then a stable hash stands in (the URL stays in the ResearchResult)."""
    if privacy.is_personal(url) or len(url) > 500:
        return "url:sha256:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return url


async def _from_memory(question: str, store: Any, scope: Scope) -> list[Any]:
    if store is None or not hasattr(store, "search"):
        return []
    hits = await store.search(question, kinds={"knowledge"}, scope=scope, k=5)
    need = min(3, len(extract_keywords(question, 12))) or 1  # conservative: most of the question covered
    out = []
    for h in hits:
        if _field(h, "status") != "verified":
            continue
        body = f"{_field(h, 'title') or ''} {_field(h, 'body') or ''}"
        if keyword_overlap(question, body) >= need:
            out.append(h)
    return out


def _pick_urls(results: list[SearchResult], limit: int) -> list[SearchResult]:
    """Prefer distinct registrable domains (independence needs them), then fill up."""
    first, rest, seen = [], [], set()
    for r in results:
        d = registrable_domain(r.url)
        (rest if d in seen else first).append(r)
        seen.add(d)
    return (first + rest)[:limit]


def _evaluate(raw: RawClaim, sources: dict[str, PageDoc], norm_text: dict[str, str], ttl: int,
              overrides: TrustOverrides | None) -> Claim | None:
    refs: list[SourceRef] = []
    pages: list[PageDoc] = []
    for sup in raw.support:
        page = sources.get(sup.source)
        if page is None or any(r.url == page.final_url for r in refs):
            continue
        if not quote_ok(sup.quote, norm_text[sup.source]):
            continue
        refs.append(SourceRef(page.final_url, registrable_domain(page.final_url),
                              source_class(page.final_url, overrides), norm_quote(sup.quote).strip(" \"'")))
        pages.append(page)
    if not refs:
        return None
    clean = [(r, p) for r, p in zip(refs, pages, strict=True) if not p.suspicious]
    clean_indep = independent_count([(r.domain, p.text) for r, p in clean])
    storable = [(r, p) for r, p in clean if not p.noindex]
    store_indep = independent_count([(r.domain, p.text) for r, p in storable])
    trusts = [trust_score(r.source_class, ttl_days=ttl, independent_agreeing=max(0, clean_indep - 1),
                          suspicious=p.suspicious) for r, p in zip(refs, pages, strict=True)]
    trust = max(trusts)
    has_ab = any(r.source_class in ("A", "B") for r, _ in storable)
    if store_indep >= 2 and has_ab:
        status = "verified"
    elif trust >= 0.4:
        status = "probable"
    else:
        status = "hypothesis"
    code = raw.code if raw.code and any(code_ok(raw.code, p) for p in pages) else None
    return Claim(kind=raw.kind, key=raw.key, text=raw.claim, sources=refs, status=status,  # type: ignore[arg-type]
                 trust=round(trust, 3), independent=clean_indep, code=code, applies_to=raw.applies_to)


_FOREIGN = re.compile("[ışğñãõçèêàâîôûœ¿¡łąężśćńřěčšžůățș]")  # no re.I: it would make "ı" match every "i"


def _lang_ok(page: PageDoc, ans_lang: str) -> bool:
    """Only pages in the answer language or English are read (P2 bench r01: a Turkish page turned the
    answer to a Hungarian question Turkish). The HTML lang tag decides; without one, the text."""
    tag = (page.lang or "").strip().lower()[:2]
    lang = tag if len(tag) == 2 and tag.isalpha() else detect_lang(page.text[:4000])
    if lang not in (ans_lang, "en", "unknown"):
        return False
    sample = page.text[:4000].lower()  # no/wrong tag: letters neither Hungarian nor English use (tr, es, pt, fr, pl, cs, ro)
    return len(_FOREIGN.findall(sample)) < max(5, len(sample) // 400)


def _compose(claims: list[Claim], lang: str, offline: bool) -> str:
    lab = _LABELS[lang]
    if not claims:
        return lab["offline"] if offline else lab["none"]
    lines = []
    for c in claims:
        domains = ", ".join(dict.fromkeys(r.domain for r in c.sources))
        # 2 independent but no A/B source → not "verified", yet not "one source" either (P2 bench 2026-11-22)
        label = (lab["probable_many"].format(n=c.independent) if c.status == "probable" and c.independent >= 2
                 else lab[c.status])
        lines.append(f"- {c.text} ({label}: {domains})")
        if c.code:
            lines.append(f"```\n{c.code.strip()}\n```")
    return "\n".join(lines)


async def _record_sources(c: Claim, store: Any, infos: dict[str, SourceInfo]) -> None:
    """AI-3's `sources` table (01/04): one row per cited page (title, domain, trust). Best effort:
    a refused URL (privacy gate) only loses the row, never the knowledge item."""
    put = getattr(store, "put_source", None)
    if put is None:
        return
    for r in c.sources:
        info = infos.get(r.url)
        try:
            await put(r.url, title=info.title if info else "", domain=r.domain,
                      trust=info.trust if info else c.trust, trust_reasons={"class": r.source_class})
        except Exception:  # PrivacyRejected / StoreError: the provenance row still cites the URL (or its hash)
            continue


async def _store_claim(c: Claim, *, store: Any, scope: Scope, lang: str, ttl: int, model: str) -> str | None:
    """Write one verified claim through the store API (privacy gate). Duplicates are not re-added."""
    item_id = "k_web_" + hashlib.sha256(f"{c.key}\n{fold(c.text)}".encode()).hexdigest()[:16]
    hits = await store.search(c.text, kinds={"knowledge"}, scope=scope, k=8) if hasattr(store, "search") else []
    for h in hits:
        hid = str(_field(h, "item_id", "id"))
        claim_part = str(_field(h, "body") or "").split("\n\n", 1)[0]
        if hid == item_id or (_field(h, "status") == "verified" and text_similar(c.text, claim_part) >= 0.82):
            return hid  # already known: no duplicate card (03/04 §5)
    quotes = "\n".join(f'> "{r.quote}" ({r.domain})' for r in c.sources)
    item = KnowledgeItem(
        id=item_id, kind=_KIND_TO_ITEM.get(c.kind, "fact"), lang=lang,  # type: ignore[arg-type]
        title=(c.key or c.text)[:120], body=f"{c.text}\n\n{quotes}", status="verified",
        verification="multi_source", trust=c.trust, topic=c.key or None,
        tags=["web", "class:" + min(r.source_class for r in c.sources)], version_tag=c.applies_to, ttl_days=ttl,
    )
    prov = [Provenance("derived_from", "source", _ref_id(r.url)) for r in c.sources]
    prov.append(Provenance("generated_by", "model", model))
    return await store.put(item, prov)


async def research(
    question: str,
    *,
    llm: Any,
    scheduler: Any,
    store: Any,
    search: SearchAdapter,
    fetcher: Fetcher,
    scope: Scope = GUEST,
    lang: str | None = None,
    on_event: Listener | None = None,
    prompt_lang: str = "en",
    priority: Priority = Priority.CHAT,
    max_pages: int = 3,
    use_memory: bool = True,
    learn: bool = True,
    names: tuple[str, ...] = (),
    runs_dir: Path | None = None,
    overrides: TrustOverrides | None = None,
    router: SimpleRouter | None = None,
) -> ResearchResult:
    """Answer `question` from the web with checked quotes; store only corroborated claims.
    Never raises for web/model failures: returns a ResearchResult (kind give_up + reason_hu)."""
    q = " ".join(question.split())[:2000]
    ans_lang = answer_lang(q, lang)
    episode = f"rs_{_b36(int(time.time()))}{secrets.token_hex(2)}"
    journal = Journal(runs_dir / episode / "journal.jsonl" if runs_dir else None, on_event)
    budget = _Budget()
    model = (router or SimpleRouter()).chat_model()[0]
    res = ResearchResult(question=q, kind="give_up", end_state=EndState.GIVE_UP, answer="", episode_id=episode,
                         lang=ans_lang)

    def finish(kind: str, end: EndState, reason: str | None = None) -> ResearchResult:
        res.kind, res.end_state, res.reason_hu = kind, end, reason  # type: ignore[assignment]
        res.llm_calls, res.searches, res.pages = budget.llm_calls, budget.searches, budget.pages
        res.tokens_out, res.wall_ms = budget.tokens_out, budget.wall_ms
        if not res.answer:
            res.answer = _compose(res.claims, ans_lang, offline=not res.web_checked and not res.from_memory)
        journal.write("done", kind=res.kind, end_state=str(end), claims=len(res.claims), stored=len(res.stored),
                      llm_calls=res.llm_calls, searches=res.searches, pages=res.pages, wall_ms=res.wall_ms,
                      reason=reason)
        return res

    journal.write("start", chars=len(q), lang=ans_lang, model=model, prompt_lang=prompt_lang)
    if len(extract_keywords(q, 12)) < 2:
        return finish("give_up", EndState.GIVE_UP, "túl rövid kérdés a kereséshez")
    try:
        # 1. the store first: verified knowledge → no web (03/01 §1)
        if use_memory:
            known = await _from_memory(q, store, scope)
            if known:
                lab = _LABELS[ans_lang]["memory"]
                res.from_memory = True
                res.answer = "\n".join(f"- {_field(h, 'body') or _field(h, 'title')} ({lab})" for h in known[:3])
                journal.write("recall", hits=len(known))
                return finish("answered", EndState.DONE)

        # 2. search (redacted; personal questions never leave the machine)
        queries = expand_query(q, max_variants=budget.limits.web_searches, names=names)
        if not queries or any(privacy.is_personal(v) for v in queries):
            return finish("give_up", EndState.GIVE_UP, "a kérdés személyes adatot tartalmaz, nem küldöm el keresőnek")
        results: list[list[SearchResult]] = []
        offline = True
        for v in queries[: budget.limits.web_searches]:
            if budget.over_time():
                break
            budget.searches += 1
            hits = await search.search(v, 6)
            offline = offline and bool(getattr(search, "last_offline", False)) and not hits
            results.append(hits)
            journal.write("search", n=budget.searches, hits=len(hits))
            if sum(len(r) for r in results) >= 8:
                break
        merged = merge_results(q, results, top=8)
        res.web_checked = not offline
        if not merged:
            reason = "nincs elérhető kereső (a hálózat vagy a szolgáltató nem válaszol)" if offline else \
                "a keresés nem adott találatot"
            return finish("give_up", EndState.GIVE_UP, reason)

        # 3. read pages (distinct domains first), within the page budget
        want = max(1, min(max_pages, budget.limits.web_pages))
        candidates = _pick_urls(merged, budget.limits.web_pages)
        pages: list[PageDoc] = []
        for batch_start in range(0, len(candidates), want):
            if len(pages) >= want or budget.pages >= budget.limits.web_pages or budget.over_time():
                break
            batch = candidates[batch_start: batch_start + (want - len(pages))]
            batch = batch[: budget.limits.web_pages - budget.pages]
            budget.pages += len(batch)
            outs = await asyncio.gather(*(fetcher.fetch(r.url) for r in batch))
            for r, o in zip(batch, outs, strict=True):
                journal.write("read", domain=registrable_domain(r.url), ok=o.page is not None, reason=o.reason,
                              chars=len(o.page.text) if o.page else 0, suspicious=bool(o.page and o.page.suspicious))
                if o.page is not None and o.page.text.strip():
                    pages.append(o.page)
        if pages and not (kept := [pg for pg in pages if _lang_ok(pg, ans_lang)]):
            journal.write("lang_skip", n=len(pages))
            return finish("give_up", EndState.GIVE_UP, "csak más nyelvű oldalakat találtam, ezekből nem válaszolok")
        if pages and len(kept) < len(pages):
            journal.write("lang_skip", n=len(pages) - len(kept))
            pages = kept
        if not pages:
            return finish("give_up", EndState.GIVE_UP, "egyik találat oldalát sem tudtam elolvasni")
        res.sources = [SourceInfo(p.final_url, registrable_domain(p.final_url), p.title,
                                  source_class(p.final_url, overrides),
                                  trust_score(source_class(p.final_url, overrides), suspicious=p.suspicious),
                                  p.suspicious) for p in pages]

        # 4. extract (one batched JSON call; at most one JSON-fix request)
        sources = {f"S{i + 1}": p for i, p in enumerate(pages)}
        prompts = load_prompts(prompt_lang, kind="research")
        listing = "; ".join(f"{sid} = {registrable_domain(p.final_url)}" for sid, p in sources.items())
        user = prompts.render("extract", topic=q.replace("{{", "{ {"), answer_language=_LANG_NAME[prompt_lang][ans_lang],
                              sources=listing)
        blocks = "\n\n".join(web_block(sid, p, relevant_text(p, q)) for sid, p in sources.items())
        messages = [{"role": "system", "content": prompts.render("system")},
                    {"role": "user", "content": f"{user}\n\n{blocks}"}]
        data = None
        for attempt in range(2):
            if budget.llm_calls >= budget.limits.llm_calls or budget.over_time():
                break
            num_predict = min(OUT_TOKENS, budget.limits.out_tokens - budget.tokens_out)
            if num_predict < 200:
                break
            async with scheduler.lease(priority, model) as lease:
                if lease.preempt.is_set():
                    raise Cancelled("preempted before the call")
                reply = await chat_or_abort(llm, lease, messages, format=EXTRACT_SCHEMA, num_predict=num_predict,
                                       temperature=TEMPERATURE, options={"seed": 42})
            budget.llm_calls += 1
            budget.tokens_out += reply.stats.eval_tokens
            data = _parse(reply.text)
            journal.write("extract", attempt=attempt, ok=data is not None, out_tokens=reply.stats.eval_tokens,
                          ms=reply.stats.total_ms, done_reason=reply.stats.done_reason)
            if data is not None or reply.stats.done_reason in ABORTED:
                break
            messages += [{"role": "assistant", "content": "(invalid output removed)"},
                         {"role": "user", "content": prompts.render("json_fix")}]
        raw = parse_claims(data)

        # 5. verify quotes + corroborate
        norm_text = {sid: norm_quote(p.text) for sid, p in sources.items()}
        ttl = ttl_days_for_query(q)
        claims: list[Claim] = []
        for rc in raw:
            c = _evaluate(rc, sources, norm_text, ttl, overrides)
            if c is None:
                res.rejected_claims += 1
                journal.write("verify", key=rc.key[:60], ok=False)
                continue
            claims.append(c)
            journal.write("verify", key=c.key[:60], ok=True, status=c.status, sources=len(c.sources),
                          independent=c.independent)
        order = {"verified": 0, "probable": 1, "hypothesis": 2}
        res.claims = sorted(claims, key=lambda c: (order[c.status], -c.trust))

        # 6. store: only verified claims, through the privacy gate
        if learn and store is not None and hasattr(store, "put"):
            for c in res.claims:
                if c.status != "verified":
                    res.withheld += 1
                    continue
                try:
                    c.stored_id = await _store_claim(c, store=store, scope=scope, lang=ans_lang, ttl=ttl, model=model)
                    if c.stored_id:
                        res.stored.append(c.stored_id)
                        await _record_sources(c, store, {si.url: si for si in res.sources})
                    journal.write("store", key=c.key[:60], ok=True)
                except PrivacyRejected:
                    res.withheld += 1
                    journal.write("store", key=c.key[:60], ok=False, reason="privacy gate")
                except Exception as e:  # a store refusal must not lose the answer
                    res.withheld += 1
                    journal.write("store", key=c.key[:60], ok=False, reason=type(e).__name__)
        else:
            res.withheld += len(res.claims)

        if not res.claims:
            reason = "a kivont állítások idézete nem szerepelt a forrásban" if raw else \
                "a modell nem adott használható állítást"
            return finish("give_up", EndState.GIVE_UP, reason)
        kind = "answered" if any(c.status != "hypothesis" for c in res.claims) else "partial"
        return finish(kind, EndState.DONE)
    except Cancelled:
        return finish("give_up", EndState.PAUSED, "megszakítva: magasabb prioritású kérés kapta meg a modellt")
    except Exception as e:  # Ollama down, store down, … — never the user's fault
        msg = getattr(e, "user_message", None) or type(e).__name__
        journal.write("infra_error", kind=type(e).__name__)
        return finish("give_up", EndState.GIVE_UP, f"infrastruktúra: {msg}")


def _parse(text: str) -> Any | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None
