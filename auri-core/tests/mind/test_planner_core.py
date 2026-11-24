"""Planner (P5) core: plan model, DAG validation, scheduling order, manifest, repo map, workspace.
Fictional data only (a todo API, 07/05)."""

import dataclasses

import pytest

from auri_core.planner import (
    Dependency,
    PlanError,
    Workspace,
    manifest_from_plan,
    next_ready,
    plan_from_dict,
    plan_to_dict,
    repo_map,
    toposort,
    validate,
    validate_manifest,
)
from auri_core.planner.workspace import WorkspaceError


def t(id, ms, kind, writes, reads=(), deps=(), accept=None):
    return {"id": id, "milestone": ms, "title": f"{id} feladat.", "kind": kind, "writes": list(writes),
            "reads": list(reads), "depends_on": list(deps),
            "accept": accept if accept is not None else [{"kind": "parse", "target": writes[0] if writes else ""}]}


def plan_dict():
    return {
        "acceptance": ["AC1: 5 végpont", "AC2: npm test zöld"],
        "scaffold": ["package.json"],
        "milestones": [{"id": "M1", "title": "Alap"}, {"id": "M2", "title": "Tesztek"},
                       {"id": "M3", "title": "Tárolás"}, {"id": "M4", "title": "HTTP"}],
        "tasks": [
            t("F2", "M1", "contract", ["src/contract.js"]),
            t("F3", "M2", "test", ["test/repo.test.js"], ["src/contract.js"], ["F2"],
              [{"kind": "red-test", "target": "test/repo.test.js"}]),
            t("F4", "M2", "test", ["test/api.test.js"], ["src/contract.js"], ["F2"],
              [{"kind": "red-test", "target": "test/api.test.js"}]),
            t("F5", "M3", "code", ["src/repo.js"], ["src/contract.js", "test/repo.test.js"], ["F3"],
              [{"kind": "test", "target": "test/repo.test.js"}]),
            t("F6", "M4", "code", ["src/app.js"], ["src/contract.js", "src/repo.js", "test/api.test.js"], ["F4", "F5"],
              [{"kind": "test", "target": "test/api.test.js"}]),
            t("F7", "M4", "code", ["src/server.js"], ["src/app.js"], ["F6"], [{"kind": "smoke", "target": "src/server.js"}]),
            t("F8", "M4", "doc", ["README.md"], ["package.json"], ["F7"],
              [{"kind": "guard", "target": "README.md"}, {"kind": "critic", "target": "README.md"}]),
        ],
    }


def mk(mutate=None):
    d = plan_dict()
    if mutate:
        mutate(d)
    return plan_from_dict(d, goal="todo REST API tesztekkel")


def task(d, tid):
    return next(x for x in d["tasks"] if x["id"] == tid)


def test_valid_plan_and_order():
    p = mk()
    assert validate(p) == []
    assert toposort(p.tasks)[0] == "F2"
    assert next_ready(p).id == "F2"
    p.task("F2").status = "done"
    assert next_ready(p).id == "F3"  # critical path (F3→F5→F6→F7→F8) before F4


def _set(tid, key, value):
    return lambda d: task(d, tid).__setitem__(key, value)


def _add(extra):
    return lambda d: d["tasks"].append(extra)


BAD = [
    ("körkörös függőség", _set("F2", "depends_on", ["F8"])),
    ("két író", _set("F7", "writes", ["src/app.js"])),
    ("nincs gépi ellenőrzés", _set("F8", "accept", [{"kind": "critic", "target": "README.md"}])),
    ("nem őse", _set("F5", "reads", ["src/contract.js", "test/api.test.js"])),
    ("ugyanaz a feladat írja a tesztet és a kódot", _set("F5", "accept", [{"kind": "test", "target": "src/repo.js"}])),
    ("nem előtte készül", _set("F5", "accept", [{"kind": "test", "target": "test/api.test.js"}])),
    ("ismeretlen függőség", _set("F7", "depends_on", ["F6", "F99"])),
    ("ismétlődő feladat-azonosító", _add(t("F2", "M1", "doc", ["docs/x.md"]))),
    ("érvénytelen útvonal", _set("F8", "writes", ["../kivul.md"])),
    ("érvénytelen útvonal", _set("F8", "writes", ["C:/Users/x.md"])),
    ("egy feladat egy fájlt írjon", _set("F7", "writes", ["src/server.js", "src/extra.js"])),
    ("kód-feladat tesztfájlt ír", _set("F7", "writes", ["test/server.test.js"])),
    ("egy feladat sem olvassa", _add(t("F9", "M4", "research", ["notes/express.md"], deps=["F2"]))),
    ("befagyasztott szerződést", _add(t("F9", "M4", "edit", ["src/contract.js"], deps=["F2"]))),
    ("nem függ az írójától", _add(t("F9", "M4", "edit", ["src/repo.js"], deps=["F2"]))),
    ("ismeretlen mérföldkő", _set("F8", "milestone", "M9")),
    ("ismeretlen feladattípus", _set("F8", "kind", "magic")),
    ("ismeretlen ellenőrzés", _set("F8", "accept", [{"kind": "vibes", "target": ""}, {"kind": "guard"}])),
    ("keret", _set("F8", "budget", {"max_attempts": 9})),
    ("senki nem írja", _set("F7", "reads", ["src/nincs.js"])),
    ("a váz fájlját írja", _set("F8", "writes", ["package.json"])),
    ("nincs kimeneti fájl", _set("F7", "writes", [])),
]


@pytest.mark.parametrize(("expect", "mutate"), BAD, ids=[f"{i}-{b[0][:20]}" for i, b in enumerate(BAD)])
def test_bad_plans_are_rejected(expect, mutate):
    errs = validate(mk(mutate))
    assert any(expect in e for e in errs), errs


def test_size_caps():
    many = mk(lambda d: d["tasks"].extend(
        t(f"G{i}", "M4", "doc", [f"docs/g{i}.md"], deps=["F2"]) for i in range(30)))
    errs = validate(many)
    assert any("túl sok feladat" in e for e in errs) and any("mérföldkövenként" in e for e in errs)
    seven = mk(lambda d: d.__setitem__("milestones", [{"id": f"M{i}", "title": "x"} for i in range(1, 8)]))
    assert any("mérföldkövek száma" in e for e in validate(seven))


def test_parse_tolerance_and_roundtrip():
    d = plan_dict()
    task(d, "F5")["dependsOn"] = task(d, "F5").pop("depends_on")
    task(d, "F7")["accept"] = ["smoke:src/server.js"]
    p = plan_from_dict(d, goal="g")
    assert p.task("F5").depends_on == ("F3",) and p.task("F7").accept[0].target == "src/server.js"
    again = plan_from_dict(plan_to_dict(p))
    assert plan_to_dict(again) == plan_to_dict(p) and validate(again) == []
    flat = plan_from_dict({"tasks": [t("A1", "", "doc", ["a.md"])]})
    assert flat.milestones[0].id == "M1" and validate(flat) == []
    for bad in ("nem terv", {"tasks": []}, {"tasks": [{"title": "nincs id"}]}, {"tasks": [t("A", "M1", "doc", ["a"])],
                                                                               "milestones": "x"}):
        with pytest.raises(PlanError):
            plan_from_dict(bad)


FILES = {
    "package.json": '{"name": "todo", "scripts": {"test": "node --test"}}',
    "src/contract.js": "export const ROUTES = {};\nexport const TITLE_MAX = 200;\n",
    "test/repo.test.js": "import { createRepo } from '../src/repo.js';\n",
    "test/api.test.js": "import { createApp } from '../src/app.js';\n",
    "src/repo.js": "import { TITLE_MAX } from './contract.js';\nexport function createRepo(path) { return {}; }\n",
    "src/app.js": "import { ROUTES } from './contract.js';\nimport { createRepo } from './repo.js';\n"
                  "export function createApp(repo) { return {}; }\n",
    "src/server.js": "import { createApp } from './app.js';\n",
    "README.md": "# todo\n",
}


def test_manifest_from_plan_is_valid_and_complete():
    m = manifest_from_plan(mk(), FILES, name="todo", kind="node", commands={"test": "node --test"},
                           deps=[Dependency("express", "5.1.0")])
    by = {f.path: f for f in m.files}
    assert validate_manifest(m, plan=mk(), allowlist={"express"}) == []
    assert by["src/contract.js"].role == "contract" and by["src/contract.js"].frozen
    assert by["test/api.test.js"].role == "test" and by["src/app.js"].owner == "F6"
    assert by["package.json"].owner == "scaffold" and by["src/app.js"].sha.startswith("sha256:")
    assert by["src/app.js"].depends_on == ("src/contract.js", "src/repo.js")
    assert by["src/app.js"].exports == ("function createApp(repo)",)


def test_manifest_errors():
    files = dict(FILES, **{"src/contract.js": "import { x } from './app.js';\nexport const A = 1;\n"})
    m = manifest_from_plan(mk(), files, name="", kind="cobol", commands={},
                           deps=[Dependency("left-pad", "1.0.0")])
    m.files.append(dataclasses.replace(m.files[0], path="docs/x.md", owner="F99"))
    m.files.append(m.files[0])
    errs = validate_manifest(m, plan=mk(), allowlist={"express"})
    for want in ("nincs neve", "ismeretlen projekttípus", "tesztparancs", "körkörös import", "nincs az engedélylistán",
                 "ismeretlen tulajdonos", "kétszer szerepel"):
        assert any(want in e for e in errs), (want, errs)


def test_repo_map_python_and_js():
    src = {"pkg/core.py": "MAX = 3\n\ndef double(n: int) -> int:\n    return n * 2\n\nclass Repo:\n    pass\n\n"
                          "def _hidden():\n    pass\n",
           "src/a.js": "export async function load(id) {}\nexport const LIMIT = 5;\nfunction local() {}\n"}
    rm = repo_map(src)
    assert "pkg/core.py: MAX; def double(n: int) -> int; class Repo" in rm and "_hidden" not in rm
    assert "src/a.js: function load(id); const LIMIT" in rm and "local" not in rm


def test_workspace_commit_reset_disk_and_reload(tmp_path):
    ws = Workspace({"a.txt": "1"}, root=tmp_path / "w", checkpoint_dir=tmp_path / "ck")
    c1 = ws.commit()
    ws.write("b/c.txt", "2")
    ws.write("a.txt", "changed")
    c2 = ws.commit()
    ws.reset(c1)
    assert ws.files == {"a.txt": "1"} and not (tmp_path / "w" / "b" / "c.txt").exists()
    assert (tmp_path / "w" / "a.txt").read_text(encoding="utf-8") == "1"
    fresh = Workspace(checkpoint_dir=tmp_path / "ck")  # a new process: snapshots come from disk
    fresh.reset(c2)
    assert fresh.files == {"a.txt": "changed", "b/c.txt": "2"}
    with pytest.raises(WorkspaceError):
        ws.write("../kint.txt", "x")
    with pytest.raises(WorkspaceError):
        fresh.reset("nincs-ilyen")
