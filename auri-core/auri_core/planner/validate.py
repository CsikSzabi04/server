"""Plan validation and scheduling order (07/01 §4–§5, 07/02 §2). Error texts are Hungarian.

Rules: acyclic (Kahn) · unique ids · known deps/milestones · one file — one writer (an `edit` task may
change a file only after its writer, never a contract) · every task has a gating (non-critic) check ·
read closure (a read comes from the scaffold or an ancestor's writes) · test before code, from another
task · research output must be read later · size caps · safe relative paths.
"""

from __future__ import annotations

import re
from collections import deque

from .model import CHECK_KINDS, TASK_KINDS, Plan, PlanTask

MAX_MILESTONES = 6
MAX_TASKS = 30  # 07/01 §5 (after P5); above this it is a project → ask which part first
MAX_TASKS_PER_MILESTONE = 8
MAX_DEPTH = 12  # longest dependency chain (tasks)
MAX_READS = 8
MAX_ATTEMPTS = 4  # 1 + 3 repair rounds
MAX_TOKENS_OUT = 2000  # num_predict ceiling per call (07/02 §6: 1000; e5 2026-11-24: test files cut off)
MAX_WALL_S = 1200  # 20 minutes per task
_ID = re.compile(r"^[A-Za-z][\w.\-]{0,31}$")
_PATH = re.compile(r"^[\w\-][\w.\-]*(?:/[\w\-][\w.\-]*)*$")
_TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]+$|[._-]test\.[a-z]+$|_test\.py$|\.spec\.[a-z]+$")
MULTI_WRITE_KINDS = {"scaffold", "integrate", "config"}


def is_safe_path(p: str) -> bool:
    return bool(_PATH.match(p)) and ".." not in p.split("/") and len(p) <= 200


def is_test_path(p: str) -> bool:
    return bool(_TEST_PATH.search(p))


def toposort(tasks: list[PlanTask]) -> list[str] | None:
    """Kahn's algorithm over known deps; None when there is a cycle."""
    ids = {t.id for t in tasks}
    indeg = {t.id: 0 for t in tasks}
    children: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for d in set(t.depends_on):
            if d in ids and d != t.id:
                indeg[t.id] += 1
                children[d].append(t.id)
            elif d == t.id:
                return None
    q = deque(sorted(i for i, n in indeg.items() if n == 0))
    order: list[str] = []
    while q:
        cur = q.popleft()
        order.append(cur)
        for c in sorted(children[cur]):
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    return order if len(order) == len(tasks) else None


def ancestors(plan: Plan) -> dict[str, set[str]]:
    """Transitive dependsOn per task (assumes an acyclic plan; unknown deps are ignored)."""
    by = plan.by_id()
    memo: dict[str, set[str]] = {}

    def anc(tid: str, stack: frozenset[str] = frozenset()) -> set[str]:
        if tid in memo:
            return memo[tid]
        out: set[str] = set()
        for d in by[tid].depends_on:
            if d in by and d not in stack:
                out.add(d)
                out |= anc(d, stack | {tid})
        memo[tid] = out
        return out

    return {t.id: anc(t.id) for t in plan.tasks}


def descendants(plan: Plan, task_id: str) -> set[str]:
    anc = ancestors(plan)
    return {t for t, a in anc.items() if task_id in a}


def chain_lengths(plan: Plan) -> dict[str, int]:
    """Longest path (in tasks) from each task to a sink — the critical-path priority."""
    order = toposort(plan.tasks) or [t.id for t in plan.tasks]
    by = plan.by_id()
    children: dict[str, list[str]] = {t.id: [] for t in plan.tasks}
    for t in plan.tasks:
        for d in t.depends_on:
            if d in children:
                children[d].append(t.id)
    length: dict[str, int] = {}
    for tid in reversed(order):
        length[tid] = 1 + max((length.get(c, 0) for c in children[tid]), default=0)
    return {tid: length.get(tid, 1) for tid in by}


def owners(plan: Plan) -> dict[str, str]:
    """file → the (non-edit) task that writes it."""
    out: dict[str, str] = {}
    for t in plan.tasks:
        if t.kind != "edit":
            for f in t.writes:
                out.setdefault(f, t.id)
    return out


def validate(plan: Plan) -> list[str]:
    errs: list[str] = []
    ms_ids = [m.id for m in plan.milestones]
    if not plan.tasks:
        return ["a tervben nincs feladat"]
    if len(set(ms_ids)) != len(ms_ids):
        errs.append("ismétlődő mérföldkő-azonosító")
    if not 1 <= len(plan.milestones) <= MAX_MILESTONES:
        errs.append(f"a mérföldkövek száma {len(plan.milestones)}, megengedett 1–{MAX_MILESTONES}")
    if len(plan.tasks) > MAX_TASKS:
        errs.append(f"túl sok feladat ({len(plan.tasks)} > {MAX_TASKS}): ez már projekt, bontsd részekre")
    for m in plan.milestones:
        n = sum(t.milestone == m.id for t in plan.tasks)
        if n > MAX_TASKS_PER_MILESTONE:
            errs.append(f"{m.id}: {n} feladat, mérföldkövenként legfeljebb {MAX_TASKS_PER_MILESTONE}")
        errs += [f"{m.id} kapuja: ismeretlen ellenőrzés: {c.kind}" for c in m.gate if c.kind not in CHECK_KINDS]
    for p in plan.scaffold:
        if not is_safe_path(p):
            errs.append(f"váz: érvénytelen útvonal: {p}")

    seen: set[str] = set()
    for t in plan.tasks:
        if t.id in seen:
            errs.append(f"{t.id}: ismétlődő feladat-azonosító")
        seen.add(t.id)
        if not _ID.match(t.id):
            errs.append(f"{t.id}: érvénytelen azonosító")
        if t.milestone not in ms_ids:
            errs.append(f"{t.id}: ismeretlen mérföldkő: {t.milestone or '(üres)'}")
        if t.kind not in TASK_KINDS:
            errs.append(f"{t.id}: ismeretlen feladattípus: {t.kind or '(üres)'}")
        if not t.title:
            errs.append(f"{t.id}: nincs leírás (title)")
        for d in t.depends_on:
            if d == t.id:
                errs.append(f"{t.id}: önmagától függ")
            elif d not in {x.id for x in plan.tasks}:
                errs.append(f"{t.id}: ismeretlen függőség: {d}")
        for c in t.accept:
            if c.kind not in CHECK_KINDS:
                errs.append(f"{t.id}: ismeretlen ellenőrzés: {c.kind}")
        if not any(c.gating and c.kind in CHECK_KINDS for c in t.accept):
            errs.append(f"{t.id}: nincs gépi ellenőrzés")
        for f in (*t.writes, *t.reads):
            if not is_safe_path(f):
                errs.append(f"{t.id}: érvénytelen útvonal: {f}")
        if t.kind not in MULTI_WRITE_KINDS and len(t.writes) > 1:
            errs.append(f"{t.id}: {len(t.writes)} fájlt ír; egy feladat egy fájlt írjon (bontsd fel)")
        if t.kind in ("contract", "test", "code", "doc", "research", "edit") and not t.writes:
            errs.append(f"{t.id}: nincs kimeneti fájl (writes)")
        if len(t.reads) > MAX_READS:
            errs.append(f"{t.id}: túl sok bemenet ({len(t.reads)} > {MAX_READS}), használj aláírásokat")
        b = t.budget
        if not (1 <= b.max_attempts <= MAX_ATTEMPTS and 1 <= b.max_tokens_out <= MAX_TOKENS_OUT
                and 1 <= b.max_wall_s <= MAX_WALL_S):
            errs.append(f"{t.id}: a keret kívül esik a határokon (≤ {MAX_ATTEMPTS} próba, "
                        f"≤ {MAX_TOKENS_OUT} token, ≤ {MAX_WALL_S} s)")

    # one file — one writer
    first: dict[str, str] = {}
    for t in plan.tasks:
        if t.kind == "edit":
            continue
        for f in t.writes:
            if f in first and first[f] != t.id:
                errs.append(f"{f}: két író ({first[f]}, {t.id})")
            first.setdefault(f, t.id)
        for f in t.writes:
            if f in plan.scaffold and t.kind != "scaffold":
                errs.append(f"{t.id}: a váz fájlját írja: {f} (csak edit feladattal)")

    order = toposort(plan.tasks)
    if order is None:
        return [*errs, "körkörös függőség"]
    anc = ancestors(plan)
    own = owners(plan)
    kinds = {t.id: t.kind for t in plan.tasks}
    by = plan.by_id()
    for tid in order:
        t = by[tid]
        for r in t.reads:
            w = own.get(r)
            if r in plan.scaffold or (w is not None and w in anc[tid]):
                continue
            if w is None:
                errs.append(f"{tid} olvassa: {r}, de senki nem írja (és a vázban sincs)")
            elif w != tid:
                errs.append(f"{tid} olvassa: {r}, de az írója ({w}) nem őse")
        if t.kind == "edit":
            for f in t.writes:
                w = own.get(f)
                if w is None and f not in plan.scaffold:
                    errs.append(f"{tid}: olyan fájlt szerkeszt, amit senki nem írt: {f}")
                elif w is not None and w not in anc[tid]:
                    errs.append(f"{tid}: a(z) {f} szerkesztése nem függ az írójától ({w})")
                elif w is not None and kinds[w] == "contract":
                    errs.append(f"{tid}: a befagyasztott szerződést ({f}) csak újratervezéssel lehet módosítani")
        # test before code, from another task (07/01 §4.4)
        for c in t.accept:
            if c.kind not in ("test", "red-test") or not c.target:
                continue
            w = own.get(c.target)
            if w == tid and t.kind != "test":
                errs.append(f"{tid}: ugyanaz a feladat írja a tesztet és a kódot ({c.target})")
            elif w is not None and w != tid and w not in anc[tid]:
                errs.append(f"{tid}: a tesztje ({c.target}) nem előtte készül (írója: {w})")
            elif w is None and c.target not in plan.scaffold:
                errs.append(f"{tid}: a tesztfájlt ({c.target}) senki nem írja")
        if t.kind == "code" and any(is_test_path(f) for f in t.writes):
            errs.append(f"{tid}: kód-feladat tesztfájlt ír")
    # research must be used (07/01 §8: lost work)
    for t in plan.tasks:
        if t.kind == "research" and t.writes:
            used = any(set(t.writes) & set(o.reads) for o in plan.tasks if o.id != t.id)
            if not used:
                errs.append(f"{t.id}: a kutatás eredményét ({', '.join(t.writes)}) egy feladat sem olvassa")
    depth = max(chain_lengths(plan).values(), default=0)
    if depth > MAX_DEPTH:
        errs.append(f"túl hosszú függőségi lánc ({depth} > {MAX_DEPTH})")
    return errs


def next_ready(plan: Plan) -> PlanTask | None:
    """The next task: deps done; critical path first, then the shorter one, then id (07/01 §4.5)."""
    done = plan.done_ids()
    ready = [t for t in plan.tasks if t.status in ("pending", "ready") and all(d in done for d in t.depends_on)]
    if not ready:
        return None
    length = chain_lengths(plan)
    return min(ready, key=lambda t: (-length[t.id], t.budget.max_tokens_out, t.id))
