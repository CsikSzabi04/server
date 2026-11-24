"""Planner (P5) with fakes only: make_plan, recipes, re-planning and the executor. No Ollama."""

import json

import pytest

from auri_core import store as real_store
from auri_core.contracts import Cancelled, Hit, LLMReply, LLMStats, Priority
from auri_core.fakes import FakeLLM, FakeScheduler, FakeStore
from auri_core.planner import (
    PLAN_SCHEMA,
    CheckResult,
    RecipeBook,
    RunBudget,
    StepResult,
    Workspace,
    execute,
    goal_signature,
    make_plan,
    make_replanner,
    merge_subtree,
    plan_from_dict,
    read_journal,
    replan_subtree,
)
from auri_core.planner.llm_call import load_prompts
from auri_core.planner.model import task_from_dict

GOAL = "Írj egy todo REST API-t tesztekkel!"


def t(id, ms, kind, writes, reads=(), deps=(), accept=None):
    return {"id": id, "milestone": ms, "title": f"{id} feladat.", "kind": kind, "writes": list(writes),
            "reads": list(reads), "depends_on": list(deps),
            "accept": accept or [{"kind": "parse", "target": writes[0]}]}


def plan_dict():
    return {
        "acceptance": ["AC1: 5 végpont"],
        "milestones": [{"id": "M1", "title": "Alap"}, {"id": "M2", "title": "Kód"}],
        "tasks": [
            t("F2", "M1", "contract", ["src/contract.js"]),
            t("F3", "M1", "test", ["test/repo.test.js"], ["src/contract.js"], ["F2"],
              [{"kind": "red-test", "target": "test/repo.test.js"}]),
            t("F5", "M2", "code", ["src/repo.js"], ["src/contract.js", "test/repo.test.js"], ["F3"],
              [{"kind": "test", "target": "test/repo.test.js"}]),
            t("F6", "M2", "code", ["src/app.js"], ["src/repo.js"], ["F5"], [{"kind": "smoke", "target": "src/app.js"}]),
        ],
    }


def cyclic():
    d = plan_dict()
    d["tasks"][0]["depends_on"] = ["F6"]
    return d


def plan():
    return plan_from_dict(plan_dict(), goal=GOAL)


# ───────────────────────────── make_plan ─────────────────────────────


async def test_make_plan_one_call_inside_a_task_lease():
    sch = FakeScheduler()
    llm = FakeLLM([plan_dict()], scheduler=sch)
    events = []
    r = await make_plan(GOAL, llm=llm, scheduler=sch, scaffold=("package.json",),
                        on_event=lambda e, d: events.append(e))
    assert r.ok and r.created_by == "model" and r.llm_calls == 1 and r.plan.scaffold == ("package.json",)
    c = llm.calls[0]
    assert c["format"] == PLAN_SCHEMA and c["num_predict"] == 2000 and c["options"] == {"seed": 42}
    assert c["temperature"] == 0.0 and [lease.prio for lease in sch.leases] == [Priority.TASK]
    assert "<goal>Írj egy todo REST API-t tesztekkel!</goal>" in c["messages"][-1]["content"]
    assert "llm" in events and r.prompt_ver.startswith("planner.en:")


async def test_invalid_json_gets_one_fix_then_invalid_plan_one_replan():
    sch = FakeScheduler()
    llm = FakeLLM(["nem json", plan_dict()], scheduler=sch)
    r = await make_plan(GOAL, llm=llm, scheduler=sch)
    assert r.ok and len(llm.calls) == 2 and llm.calls[1]["messages"][-1]["content"].startswith("Output only valid JSON")
    llm2 = FakeLLM([cyclic(), plan_dict()], scheduler=sch)
    r2 = await make_plan(GOAL, llm=llm2, scheduler=sch, acceptance=("AC9: saját",))
    assert r2.ok and len(llm2.calls) == 2 and "körkörös függőség" in llm2.calls[1]["messages"][-1]["content"]
    assert r2.plan.acceptance == ("AC9: saját",)


async def test_still_invalid_is_an_honest_failure():
    sch = FakeScheduler()
    r = await make_plan(GOAL, llm=FakeLLM([cyclic(), cyclic()], scheduler=sch), scheduler=sch)
    assert not r.ok and r.plan is None and "körkörös függőség" in r.errors and r.reason_hu.startswith("nem sikerült")
    cut = LLMReply('{"tasks": [', LLMStats(done_reason="length"))
    r2 = await make_plan(GOAL, llm=FakeLLM([cut, cut], scheduler=sch), scheduler=sch)
    assert not r2.ok and r2.llm_calls == 2  # cut-off: no JSON-fix request, straight to the one re-plan


async def test_empty_goal_preemption_braces_and_hu_prompts():
    sch = FakeScheduler()
    llm = FakeLLM([], scheduler=sch)
    assert not (await make_plan("  ", llm=llm, scheduler=sch)).ok and llm.calls == []
    sch.preempt_next = True
    with pytest.raises(Cancelled):
        await make_plan(GOAL, llm=llm, scheduler=sch)
    assert llm.calls == []
    sch.preempt_next = False
    llm2 = FakeLLM([plan_dict()], scheduler=sch)
    r = await make_plan("sablon {{goal}} kapcsos zárójellel", llm=llm2, scheduler=sch, prompt_lang="hu")
    assert r.ok and "{{goal}}" in llm2.calls[0]["messages"][-1]["content"] and r.prompt_ver.startswith("planner.hu:")
    assert {"system", "plan", "fix_plan", "replan", "json_fix"} <= set(load_prompts("hu").sections)


# ───────────────────────────── recipes ─────────────────────────────


class RecipeStore(FakeStore):
    """FakeStore + a search that finds knowledge items by a term in title/body (like the FTS index)."""

    async def search(self, q, *, kinds, scope, k=8):
        return [Hit("knowledge", i.id, i.title, i.body, i.status, i.trust, 1.0)
                for i in self.items.values() if q in i.title or q in i.body][:k]


async def test_recipe_save_then_plan_without_model_calls():
    st = RecipeStore()
    book = RecipeBook(st)
    assert goal_signature(GOAL) == goal_signature("irj egy TODO rest api-t, tesztekkel")
    saved = await book.save(GOAL, plan(), run_id="plan_teszt", model="gemma4:e2b")
    item = st.items[saved]
    assert item.kind == "howto" and item.status == "verified" and item.verification == "tests_passed"
    sch = FakeScheduler()
    llm = FakeLLM([], scheduler=sch)
    r = await make_plan("írj egy todo REST API-t tesztekkel", llm=llm, scheduler=sch, recipes=book)
    assert r.ok and r.created_by == "recipe" and llm.calls == [] and r.plan.version == 1
    assert all(x.status == "pending" and x.recipe == goal_signature(GOAL) for x in r.plan.tasks)
    assert await book.lookup("valami egészen más cél") is None


async def test_recipe_privacy_rejection_never_breaks():
    events = []
    book = RecipeBook(RecipeStore(reject=lambda _t: True), on_event=lambda e, d: events.append(e))
    assert await book.save(GOAL, plan(), run_id="plan_teszt") is None and "recipe.rejected" in events
    assert await RecipeBook(None).save(GOAL, plan(), run_id="x") is None


async def test_recipe_roundtrip_on_the_real_store(tmp_path):
    mem = real_store.open_store(tmp_path / "core.db")
    book = RecipeBook(mem)
    item_id = await book.save(GOAL, plan(), run_id="plan_teszt", model="gemma4:e2b")
    assert item_id and await book.save(GOAL, plan(), run_id="plan_teszt2") == item_id  # reuse → trust bump
    got = await book.lookup(GOAL)
    assert got is not None and [x.id for x in got.tasks] == ["F2", "F3", "F5", "F6"]


# ───────────────────────────── re-planning ─────────────────────────────


async def test_replan_replaces_only_the_failed_subtree():
    p = plan()
    for tid in ("F2", "F3"):
        p.task(tid).status = "done"
    sch = FakeScheduler()
    repl = {"reason": "kisebb lépések", "tasks": [
        t("F5a", "M2", "code", ["src/repo.js"], ["src/contract.js", "test/repo.test.js"], ["F3"],
          [{"kind": "test", "target": "test/repo.test.js"}]),
        t("F6", "M2", "code", ["src/app.js"], ["src/repo.js"], ["F5a"], [{"kind": "smoke", "target": "src/app.js"}])]}
    llm = FakeLLM([repl], scheduler=sch)
    new = await replan_subtree(p, p.task("F5"), digest="AssertionError: 1 != 2", llm=llm, scheduler=sch)
    assert new.version == 2 and [x.id for x in new.tasks] == ["F2", "F3", "F5a", "F6"]
    assert new.task("F2").status == "done" and new.task("F5a").status == "pending"
    msg = llm.calls[0]["messages"][-1]["content"]
    assert "F5, F6" in msg and "AssertionError" in msg and "src/contract.js" in msg
    bad = {"tasks": [t("F5b", "M2", "code", ["src/contract.js"], deps=["F2"])]}  # a finished task's file
    assert await replan_subtree(p, p.task("F5"), digest="x", llm=FakeLLM([bad], scheduler=sch), scheduler=sch) is None


# ───────────────────────────── executor ─────────────────────────────


def green_runner(fail=None, calls=None):
    """A fake step runner: writes every declared file and reports every gating check green.
    `fail(task, n)` → a StepResult to return instead (n = how many times this task ran)."""
    seen = {}

    async def run(task, ctx):
        seen[task.id] = seen.get(task.id, 0) + 1
        if calls is not None:
            calls.append(task.id)
        if fail and (r := fail(task, seen[task.id])) is not None:
            if isinstance(r, BaseException):
                raise r
            return r
        files = {f: f"// {task.id}\n" for f in task.writes}
        return StepResult(True, files, [CheckResult(c.kind, c.target, True, 5) for c in task.accept if c.gating],
                          tokens_out=50)

    return run


async def test_happy_path_checkpoints_and_report_from_journal(tmp_path):
    calls, events = [], []
    out = await execute(plan(), runner=green_runner(calls=calls), run_dir=tmp_path,
                        on_event=lambda e, d: events.append(e))
    assert out.state == "done" and out.done == ["F2", "F3", "F5", "F6"] and calls == ["F2", "F3", "F5", "F6"]
    assert set(out.checkpoints) == {"F2", "F3", "F5", "F6"} and out.plan.contracts_hash.startswith("sha256:")
    assert out.files["src/app.js"] == "// F6\n" and out.tokens_out == 200
    assert out.report_hu.startswith(f"Kész: {GOAL} — 4/4 feladat kész, 4 zöld ellenőrzés.")
    assert "- F5 (F5 feladat.): test:test/repo.test.js" in out.report_hu
    types = [e["type"] for e in read_journal(tmp_path)]
    assert types[:2] == ["run.start", "plan.created"] and types[-1] == "run.end" and "milestone.done" in types
    assert events.count("task.done") == 4


async def test_no_green_check_means_not_done_and_foreign_files_are_refused():
    out = await execute(plan(), runner=green_runner(lambda task, n: StepResult(True, {f: "x" for f in task.writes})))
    assert out.state == "failed" and out.failed_task == "F2" and "nem mondhatom késznek" in out.report_hu
    out2 = await execute(plan(), runner=green_runner(
        lambda task, n: StepResult(True, {"src/idegen.js": "x"}, [CheckResult("parse", "", True)])
        if task.id == "F5" else None))
    assert out2.state == "failed" and out2.done == ["F2", "F3"] and "idegen fájlt írt" in out2.report_hu


async def test_failure_rolls_back_and_replans_once(tmp_path):
    p = plan()

    async def replanner(old, failed, res):
        new_tasks = [task_from_dict(t("F5b", "M2", "code", ["src/repo.js"], ["src/contract.js"], ["F3"],
                                      [{"kind": "test", "target": "test/repo.test.js"}]), "x", []),
                     task_from_dict(t("F6", "M2", "code", ["src/app.js"], ["src/repo.js"], ["F5b"],
                                      [{"kind": "smoke", "target": "src/app.js"}]), "y", [])]
        return merge_subtree(old, {"F5", "F6"}, new_tasks)

    fail_f5 = green_runner(lambda task, n: StepResult(False, digest="AssertionError: 1 != 2", signature="s1")
                           if task.id == "F5" else None)
    out = await execute(p, runner=fail_f5, run_dir=tmp_path, replanner=replanner)
    assert out.state == "done" and out.plan.version == 2 and out.replans == 1
    j = read_journal(tmp_path)
    rb = next(e for e in j if e["type"] == "rollback")
    assert rb["to"] == out.checkpoints["F3"] and rb["task"] == "F5"
    assert "Újratervezés: 1×." in out.report_hu and "F5b" in out.done


async def test_replans_are_bounded_and_infra_is_not_replanned():
    calls = []

    async def replanner(old, failed, res):
        calls.append(failed.id)
        return merge_subtree(old, set(), [])  # same tasks again, new version

    always = green_runner(lambda task, n: StepResult(False, digest="ugyanaz") if task.id == "F5" else None)
    out = await execute(plan(), runner=always, replanner=replanner)
    assert out.state == "failed" and calls == ["F5", "F5"] and out.replans == 2
    assert "Elakadt: F5" in out.report_hu
    calls.clear()
    boom = green_runner(lambda task, n: RuntimeError("sandbox le") if task.id == "F3" else None)
    out2 = await execute(plan(), runner=boom, replanner=replanner)
    assert out2.state == "failed" and calls == [] and "infrastruktúra: RuntimeError" in out2.report_hu


async def test_preemption_pauses_and_resume_continues_without_redoing_work(tmp_path):
    calls = []
    first = green_runner(lambda task, n: Cancelled("hang") if task.id == "F5" else None, calls=calls)
    out = await execute(plan(), runner=first, run_dir=tmp_path)
    assert out.state == "paused" and out.done == ["F2", "F3"] and "Szünetel" in out.report_hu
    calls.clear()
    out2 = await execute(None, runner=green_runner(calls=calls), run_dir=tmp_path, resume=True)
    assert out2.state == "done" and calls == ["F5", "F6"] and out2.run_id == out.run_id
    assert out2.files["src/contract.js"] == "// F2\n"  # restored from the checkpoint on disk
    assert "4/4 feladat kész" in out2.report_hu


async def test_ask_user_budget_gate_and_invalid_plan():
    ask = green_runner(lambda task, n: StepResult(False, needs_user="Egész szám vagy UUID? Javaslom: egész.")
                       if task.id == "F2" else None)
    out = await execute(plan(), runner=ask)
    assert out.state == "waiting_user" and out.question.startswith("Egész szám") and out.done == []
    out2 = await execute(plan(), runner=green_runner(), budget=RunBudget(max_task_runs=2))
    assert out2.state == "paused" and out2.done == ["F2", "F3"] and out2.question.endswith("Folytassam?")

    async def red_gate(ms, files):
        return [CheckResult("test", "npm test", ms.id != "M1", digest="2 failed")]

    out3 = await execute(plan(), runner=green_runner(), gate_runner=red_gate)
    assert out3.state == "failed" and "M1 mérföldkő kapuja piros" in out3.report_hu
    d = plan_dict()
    d["tasks"][1]["depends_on"] = ["F6"]
    d["tasks"][0]["depends_on"] = ["F3"]
    out4 = await execute(plan_from_dict(d, goal=GOAL), runner=green_runner())
    assert out4.state == "failed" and out4.report_hu.startswith("Érvénytelen terv")


async def test_contract_change_request_blocks_and_triggers_replan():
    seen = []

    async def replanner(old, failed, res):
        seen.append((failed.id, failed.status, res.change_request))
        return None

    cr = green_runner(lambda task, n: StepResult(False, change_request="kell updatedAt") if task.id == "F5" else None)
    out = await execute(plan(), runner=cr, replanner=replanner, workspace=Workspace())
    assert out.state == "failed" and seen == [("F5", "blocked", "kell updatedAt")]


async def test_make_replanner_binds_the_model_client():
    p = plan()
    p.task("F2").status = "done"
    sch = FakeScheduler()
    llm = FakeLLM(["nem json", "megint nem"], scheduler=sch)
    rp = make_replanner(llm=llm, scheduler=sch)
    assert await rp(p, p.task("F3"), StepResult(False, digest="x")) is None and len(llm.calls) == 2
    assert json.loads(json.dumps(PLAN_SCHEMA))["required"] == ["acceptance", "milestones", "tasks"]


def test_normalize_fixes_the_small_models_id_file_slips():
    from auri_core.planner.planning import normalize_plan_dict

    data = {"tasks": [
        {"id": "F1", "kind": "test", "writes": ["test_lista.py"], "reads": [], "depends_on": []},
        {"id": "F2", "kind": "code", "writes": ["lista.py"], "reads": ["F1"], "depends_on": ["test_lista.py"]},
        {"id": "F3", "kind": "code", "writes": ["lista.py"], "reads": ["lista.py"], "depends_on": ["F2"]},
    ]}
    t = normalize_plan_dict(data)["tasks"]
    assert t[1]["reads"] == ["test_lista.py"] and t[1]["depends_on"] == ["F1"]  # id ↔ file mixups
    assert t[2]["kind"] == "edit"  # the second writer is a descendant → an edit, not a conflict
    assert normalize_plan_dict("junk") == "junk"


async def test_invalid_model_plan_falls_back_to_the_module_plan():
    from auri_core.planner.validate import validate

    goal = "Két modul: `lista.py` (hozzaad, torol) és `formaz.py` (szoveg), unittest-tesztekkel. Ne írj config.json-t."
    sch = FakeScheduler()
    bad = {"acceptance": [], "milestones": [{"id": "M1", "title": "x"}],
           "tasks": [{"id": "F1", "milestone": "M1", "title": "a", "kind": "contract", "writes": ["lista.py"],
                      "reads": [], "depends_on": [], "accept": [{"kind": "schema", "target": "lista.py"}]},
                     {"id": "F2", "milestone": "M1", "title": "b", "kind": "contract", "writes": ["lista.py"],
                      "reads": [], "depends_on": [], "accept": [{"kind": "schema", "target": "lista.py"}]}]}
    events = []
    r = await make_plan(goal, llm=FakeLLM([bad, bad], scheduler=sch), scheduler=sch,
                        on_event=lambda e, d: events.append(e))
    assert r.ok and r.created_by == "modules" and r.llm_calls == 2 and "plan.fallback" in events
    assert [(t.id, t.kind, t.writes) for t in r.plan.tasks] == [
        ("T1", "test", ("test_lista.py",)), ("T2", "test", ("test_formaz.py",)),
        ("C1", "code", ("lista.py",)), ("C2", "code", ("formaz.py",))]
    assert validate(r.plan) == [] and "C1" in r.plan.by_id()["C2"].depends_on


async def test_a_failed_step_is_repaired_with_its_digest_before_any_replan(tmp_path):
    """e5 2026-11-24: one try per step, then an invalid 2B re-plan → 0/5. Now 1 + 3 repair rounds come first."""
    seen, base = [], green_runner()

    async def replanner(old, failed, res):
        raise AssertionError("no re-plan while repair rounds are left")

    async def flaky(task, ctx):
        if task.id == "F5" and ctx.attempt == 1:
            return StepResult(False, digest="AssertionError: 1 != 2", signature="s1")
        if task.id == "F5":
            seen.append(ctx.last_digest)
        return await base(task, ctx)

    out = await execute(plan(), runner=flaky, run_dir=tmp_path, replanner=replanner)
    assert out.state == "done" and out.replans == 0 and seen == ["AssertionError: 1 != 2"]
    types = [e["type"] for e in read_journal(tmp_path)]
    assert types.count("task.retry") == 1 and "task.failed" not in types
    same, moving = [], []
    out2 = await execute(plan(), runner=green_runner(
        lambda task, n: StepResult(False, digest="levágott válasz") if task.id == "F5" else None, calls=same))
    assert out2.state == "failed" and same.count("F5") == 2  # the same digest twice = no progress
    out3 = await execute(plan(), runner=green_runner(
        lambda task, n: StepResult(False, digest=f"got {n}") if task.id == "F5" else None, calls=moving))
    assert out3.state == "failed" and moving.count("F5") == 4  # 1 + 3 repair rounds
