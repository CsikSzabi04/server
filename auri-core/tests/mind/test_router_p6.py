"""P6 router: measured choice, lane preference, RAM, escalation ladder, robust loading (fictional numbers)."""

import json
from types import SimpleNamespace

import pytest

from auri_core.contracts import BUDGETS, Failure, Goal, Hit, Recall
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, make_task
from auri_core.router import SimpleRouter, StatsRouter, difficulty, estimate_size, load_router, scale_budget
from auri_core.routing import Record, build_table, load_bench_records, record_from_bench, tier_of, wilson_lower
from auri_core.solve import solve

E2B, Q4B, E4B, C7B = "gemma4:e2b", "qwen3.5:4b", "gemma4:e4b", "qwen2.5-coder:7b"


def recs(model, passed, n, *, lang="py", level=1, mode="+repair", ms=10_000, kind="code"):
    return [Record(kind, lang, level, model, mode, i < passed, ms) for i in range(n)]


def router(records, models=(E2B, Q4B, E4B, C7B), **kw):
    return StatsRouter(build_table(records), lane_model=E2B, models=models, **kw)


def bench_row(**kw):
    row = {"run_id": "bench_x", "task_id": "py-l1-0001", "split": "dev", "lang": "py", "level": 1,
           "mode": "model-only", "model": E2B, "pass1": True, "outcome": "pass", "wall_ms": 9000,
           "hidden": {"status": "pass"}, "false_done": False, "cloud_calls": 0}
    row.update(kw)
    return row


def test_wilson_and_tiers():
    assert wilson_lower(0, 0) == 0.0
    assert wilson_lower(10, 10) == pytest.approx(0.722, abs=0.002)
    assert wilson_lower(5, 10) == pytest.approx(0.237, abs=0.002)
    assert (tier_of(E2B), tier_of(Q4B), tier_of(E4B), tier_of(C7B), tier_of("llama3.1:8b")) == (2, 2, 3, 3, 3)


def test_record_from_bench_rules():
    assert record_from_bench(bench_row()).ok is True
    assert record_from_bench(bench_row(mode="+repair", pass_repair3=False, pass1=None)).ok is False
    assert record_from_bench(bench_row(split="heldout")) is None  # never choose a model on the exam set
    assert record_from_bench(bench_row(false_done=True)).ok is False
    assert record_from_bench(bench_row(cloud_calls=1)) is None
    old = bench_row()
    del old["pass1"]
    old["hidden"] = {"status": "fail"}
    assert record_from_bench(old).ok is False
    assert record_from_bench({"mode": "+repair"}) is None
    # an infrastructure failure is not a model failure (Ollama was down: llm_calls 0, give_up)
    down = bench_row(pass1=False, outcome="give_up", llm_calls=0, kb_hit=None,
                     reason_hu="infrastruktúra: Nem érem el az Ollamát. Fut a háttérben?")
    assert record_from_bench(down) is None
    assert record_from_bench(bench_row(llm_calls=0, kb_hit=None)) is None
    assert record_from_bench(bench_row(llm_calls=0, kb_hit="snip_1")).ok is True  # a memory hit is real
    assert record_from_bench(bench_row(pass1=False, llm_calls=2, reason_hu="infrastruktúra: sandbox")) is None


def test_loading_is_robust_and_dedups_resumed_runs(tmp_path):
    a = tmp_path / "bench_a"
    a.mkdir()
    lines = [json.dumps(bench_row(task_id=f"t{i}")) for i in range(3)]
    lines.append(json.dumps(bench_row(task_id="t0", pass1=False)))  # resumed: t0 re-run, failed
    (a / "results.jsonl").write_text("\n".join(lines) + '\n\n{"run_id": "bench_x", "task', encoding="utf-8")
    (tmp_path / "empty").mkdir()
    recs_ = load_bench_records(tmp_path)
    assert len(recs_) == 4
    t = build_table(recs_)
    c = t.get("code", "py", 1, E2B, "model-only")
    assert (c.n, c.passed) == (3, 2)
    assert load_bench_records(tmp_path / "missing") == [] and load_bench_records(None) == []


def test_lane_model_stays_unless_clearly_better():
    close = router(recs(E2B, 19, 28) + recs(Q4B, 20, 28))
    m, why = close.code_model(make_task(level=1))
    assert m == E2B and "19/28" in why and "NK14" in why
    clear = router(recs(E2B, 10, 28) + recs(Q4B, 27, 28))
    m, why = clear.code_model(make_task(level=1))
    assert m == Q4B and "váltás" in why
    nodata = router([])
    m, why = nodata.code_model(make_task(level=1))
    assert m == E2B and "nincs elég mérés" in why


def test_fallback_views_and_unmeasured_lane():
    r = router(recs(E2B, 9, 10, level=0, mode="model-only") + recs(Q4B, 8, 10, level=1))
    m, why = r.code_model(make_task(level=1))
    assert m == E2B and "code/py/*" in why  # lane measured only on a wider view → still compared
    only_other = StatsRouter(build_table(recs(Q4B, 10, 10)), lane_model=E2B, models=[E2B, Q4B])
    assert only_other.code_model(make_task(level=1))[0] == E2B  # lane unknown, not worse → stay


def test_latency_breaks_ties_and_ram_filters():
    r = router(recs(E4B, 20, 28, ms=60_000) + recs(C7B, 20, 28, ms=30_000))
    m, why = r.pick("code", "py", 1, tier=3)
    assert m == C7B and "medián 30.0 s" in why
    big = StatsRouter(build_table([]), lane_model=E2B, models=[E2B, "qwen2.5-coder:14b", "mystery:3b"])
    assert set(big.available) == {E2B, "mystery:3b"}  # 9 GB does not fit next to the e2b
    assert "embeddinggemma" not in StatsRouter(build_table([]), lane_model=E2B, models=[E2B, "embeddinggemma"]).available


def test_assess_levels_and_budget():
    r = router(recs(E2B, 19, 28))
    hit = Hit("knowledge", "k1", "t", "b", "verified", 0.9, 1.0)
    a = r.assess(Goal("mi a fővárosa?", "chat"), Recall([hit]))
    assert a.level == 0 and a.model == "" and "k1" in a.reason
    store_hit = SimpleNamespace(id="s9", status="verified")
    assert "s9" in r.assess(Goal("x", "code"), Recall([store_hit])).reason
    easy = r.assess(Goal("írj egy függvényt", "code"), Recall(known_ratio=0.9))
    assert easy.level == 2 and easy.model == E2B and easy.budget.out_tokens < BUDGETS["code"].out_tokens
    hard = r.assess(Goal("írj egy többfájlos projektet API-val", "code", freshness_risk=1.0), Recall(known_ratio=0.0),
                    history=SimpleNamespace(success_rate=lambda *a, **k: 0.1))
    assert hard.level == 3 and hard.model in (E4B, C7B) and hard.predicted_success < 0.4
    chat_hard = r.assess(Goal("x" * 3000, "chat", freshness_risk=1.0), Recall(),
                         history=SimpleNamespace(success_rate=lambda *a, **k: 0.0))
    assert chat_hard.level == 2  # chat never goes to L3
    no_l3 = router([], models=(E2B,))
    h2 = no_l3.assess(Goal("projekt", "code"), Recall(), history=SimpleNamespace(success_rate=lambda *a, **k: 0.0))
    assert h2.level == 2 and "→ L2" in h2.reason


def test_difficulty_size_budget_helpers():
    assert difficulty(1, 1, 0, 0) == 0.0 and difficulty(0, 0, 1, 1) == 1.0
    assert estimate_size("írj egy függvényt") < estimate_size("egy osztály") < estimate_size("teljes projekt")
    assert scale_budget(BUDGETS["code"], 1.0).out_tokens == int(BUDGETS["code"].out_tokens * 1.25)


def test_escalation_ladder():
    r = router(recs(E2B, 19, 28))
    assert r.escalate(0, Failure("verify")) == 2
    assert r.escalate(2, Failure("verify"), lang="py", task_level=1) == 3 and "L3" in r.last_reason
    assert r.escalate(2, Failure("missing_knowledge")) == 2 and "P2" in r.last_reason
    assert r.escalate(2, Failure("no_progress", "ModuleNotFoundError: No module named '<X>'")) == 2
    assert r.escalate(2, Failure("timeout")) == 2
    assert r.escalate(3, Failure("verify")) is None and "ki van kapcsolva" in r.last_reason
    worse = router(recs(E2B, 19, 28) + recs(E4B, 10, 28) + recs(C7B, 9, 28))
    assert worse.escalate(2, Failure("verify"), lang="py", task_level=1) is None and "nem jobb" in worse.last_reason
    cloud = router(recs(E2B, 19, 28), allow_cloud=True, cloud_model="groq:gpt-oss-120b")
    assert cloud.escalate(3, Failure("verify")) == 4
    assert cloud.escalate(3, Failure("verify"), interactive=False) is None and "soha" in cloud.last_reason
    assert cloud.escalate(2, Failure("llm_unavailable")) == 4
    assert router([], allow_cloud=True).cloud_model is None  # allowed but not configured → off
    assert r.escalate(4, Failure("verify")) is None


def test_load_router_fallbacks(tmp_path):
    cfg = SimpleNamespace(models=SimpleNamespace(code=E2B, roles=Q4B), data_dir=tmp_path)
    assert isinstance(load_router(cfg), SimpleRouter)
    (tmp_path / "eval" / "b").mkdir(parents=True)
    rows = [bench_row(task_id=f"t{i}", pass1=i < 6) for i in range(10)]
    (tmp_path / "eval" / "b" / "results.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
    r = load_router(cfg)
    assert isinstance(r, StatsRouter) and set(r.available) == {E2B, Q4B} and r.cloud_model is None
    assert r.describe()[0] == {"kind": "code", "lang": "py", "level": 1, "model": E2B, "mode": "model-only",
                               "n": 10, "passed": 6, "rate": 0.6, "lower": pytest.approx(0.313, abs=0.002),
                               "median_s": 9.0}
    assert isinstance(load_router(SimpleNamespace()), SimpleRouter)  # broken cfg → P0 router


async def test_stats_router_is_a_drop_in_for_solve():
    sch = FakeScheduler()
    llm = FakeLLM([{"files": [{"path": "solution.py", "content": "def double(n):\n    return n * 2\n"}]}],
                  scheduler=sch)
    r = router(recs(E2B, 2, 28) + recs(Q4B, 27, 28))
    out = await solve(make_task(), llm=llm, sandbox=FakeSandbox(["pass"]), store=None, scheduler=sch, router=r,
                      visible={"tests/t.py": "x"})
    assert out.kind == "pass" and llm.calls[0]["model"] == Q4B and out.model == Q4B
