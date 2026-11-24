"""AI-3 P4: maintenance (TTL, archive, refuted cleanup), dedupe, privacy audit, idle watcher state machine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from auri_core.idle import IdleConfig, IdleWatcher, maintenance_job

SEED = [{"relation": "derived_from", "ref_type": "seed", "ref_id": "s"}]


def _age(store, item_id: str, days: int, *, col: str = "created_at") -> None:
    t = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    store.db.execute(f"UPDATE knowledge_items SET {col}=?, verified_at=?, updated_at=? WHERE id=?", (t, t, t, item_id))


async def test_maintain_clocks(store):
    ttl = await store.put({"title": "React legújabb", "body": "19", "status": "verified", "ttl_days": 3}, SEED)
    old = await store.put({"title": "jQuery tipp", "body": "x", "status": "verified", "kind": "fact"}, SEED)
    used = await store.put({"title": "rekurzió", "body": "y", "status": "verified", "kind": "fact"}, SEED)
    bad = await store.put({"title": "tévhit", "body": "z"}, SEED)
    await store.demote(bad, "hamis", status="refuted")
    for iid in (ttl, old, used, bad):
        _age(store, iid, 400)
    store.mark_used([used])
    out = store.maintain()
    st = dict(store.db.execute("SELECT id, status FROM knowledge_items").fetchall())
    assert st[ttl] == "archived" or st[ttl] == "stale"  # TTL first; 400 days unused may archive it too
    assert st[old] == "archived" and st[used] == "verified" and bad not in st
    assert out["deleted"] == 1 and out["archived"] >= 1


async def test_dedupe_keeps_versions_apart(store):
    a = await store.put({"title": "lista rendezés", "body": "a sorted() új listát ad vissza", "status": "verified", "trust": 0.7}, SEED)
    b = await store.put({"title": "lista rendezés", "body": "a sorted() új listát ad vissza!", "trust": 0.3}, SEED)
    v18 = await store.put({"title": "ReactDOM render", "body": "ReactDOM.render(<App/>, root)", "version_tag": "react<19"}, SEED)
    v19 = await store.put({"title": "ReactDOM render", "body": "ReactDOM.render(<App/>, root)", "version_tag": "react>=19"}, SEED)
    pairs = store.dedupe()
    assert pairs == [(a, b)]
    st = dict(store.db.execute("SELECT id, status FROM knowledge_items").fetchall())
    assert st[b] == "archived" and st[v18] != "archived" and st[v19] != "archived"
    assert ("merged_into", "feedback", a) in [(p.relation, p.ref_type, p.ref_id) for p in await store.provenance("knowledge", b)]


async def test_audit_reports_ids_only(store):
    ok = await store.put({"title": "rekurzió", "body": "a függvény önmagát hívja"}, SEED)
    store.db.execute("INSERT INTO knowledge_items(id, kind, lang, title, body, created_at, updated_at) "
                     "VALUES ('sneaky','fact','hu','x','Teszt Elek, 1990.01.01','t','t')")  # bypassed the gate
    assert store.audit_personal() == ["sneaky"] and ok


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


async def test_watcher_studies_only_when_idle_and_pauses_fast(store, tmp_path):
    clock, idle = _Clock(), {"s": 0.0}
    started = asyncio.Event()

    async def slow(ctx):
        started.set()
        await asyncio.sleep(60)

    w = IdleWatcher(store, mode="full", flag_dir=tmp_path, input_idle=lambda: idle["s"], clock=clock,
                    wall=lambda: datetime(2026, 11, 21, 14, 0), cfg=IdleConfig(cooldown_s=300))
    w.register("heavy", slow, light=False)
    w.register("light", slow, light=True)
    assert await w.step() == "WAITING" and w.reason == "nem tétlen"
    idle["s"] = 1300  # 20+ min idle by day → only the light job may run
    assert await w.step() == "STUDYING" and w.describe()["job"] == "light"
    await started.wait()
    idle["s"] = 0.5  # the user is back
    assert await w.step() == "PAUSED" and w.last_pause_ms is not None and w.last_pause_ms < 1000
    jid = store.list_jobs(kind="bg:light")[0]
    assert jid["state"] == "paused"
    idle["s"] = 30
    assert await w.step() == "COOLDOWN"
    clock.t += 301
    assert await w.step() == "WAITING"
    idle["s"] = 1300
    assert await w.step() == "STUDYING" and store.list_jobs(kind="bg:light")[0]["id"] == jid["id"]  # resumed, same job
    w._current[1].cancel()  # type: ignore[index]


async def test_watcher_blockers_and_night_heavy(store, tmp_path):
    w = IdleWatcher(store, mode="full", flag_dir=tmp_path, input_idle=lambda: 700.0,
                    wall=lambda: datetime(2026, 11, 22, 2, 0))
    ran: list[str] = []

    async def heavy(ctx):
        ran.append("heavy")

    w.register("heavy", heavy, light=False)
    (tmp_path / "no_study").write_text("1")
    assert await w.step() == "WAITING" and "kézi tiltás" in w.reason
    (tmp_path / "no_study").unlink()
    assert await w.step() == "STUDYING"  # night: 10 min idle is enough, heavy allowed
    await asyncio.sleep(0)
    assert await w.step() == "WAITING" and ran == ["heavy"]
    assert await w.step() == "WAITING" and w.reason == "nincs esedékes munka"  # done today


async def test_maintenance_job_report(store, tmp_path):
    await store.put({"title": "a", "body": "b"}, SEED)
    w = IdleWatcher(store, mode="light", flag_dir=tmp_path, input_idle=lambda: 9999.0)
    w.register("maintenance", maintenance_job, light=True)
    assert await w.step() == "STUDYING"
    await w._current[1]  # type: ignore[index]
    await w.step()
    rep = store.list_jobs(kind="bg:maintenance")[0]
    assert rep["state"] == "done" and rep["checkpoint"]["personal_flagged"] == 0 and "merged" in rep["checkpoint"]
