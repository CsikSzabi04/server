"""recall(): POST /recall — verified only, provenance, a bounded prompt block (fictional data only)."""

from auri_core import store
from auri_core.contracts import GUEST, Hit, KnowledgeItem, Provenance, RecallRequest, Scope
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, make_task
from auri_core.recall import recall
from auri_core.solve import solve


class HitStore:
    def __init__(self, hits, prov=None):
        self.hits, self.prov, self.seen = hits, prov or {}, []

    async def search(self, q, *, kinds, scope, k=8):
        self.seen.append((q, kinds, scope, k))
        return self.hits[:k]

    async def provenance(self, item_type, item_id):
        return self.prov.get(item_id, [])


def hit(i, status="verified", body="A Föld a Nap körül kering."):
    return Hit("knowledge", f"k{i}", f"Tény {i}", body, status, 0.9, 1.0 / (i + 1))


async def test_only_verified_with_sources_and_scope_passthrough():
    st = HitStore([hit(0), hit(1, "hypothesis"), hit(2)], {"k0": [Provenance("derived_from", "source", "src_1")]})
    me = Scope("user", "u_teszt")
    r = await recall(RecallRequest("mi kering a Nap körül?"), store=st, scope=me)
    assert [i.item_id for i in r.items] == ["k0", "k2"] and r.withheld == 1
    assert r.items[0].sources == (Provenance("derived_from", "source", "src_1"),)
    assert st.seen[0][2] is me and st.seen[0][3] == 15
    assert r.prompt_block.startswith('<recall note="ellenőrzött tudás') and "[2] Tény 2" in r.prompt_block
    assert "(forrás: derived_from source)" in r.prompt_block and r.prompt_block.endswith("</recall>")


async def test_budget_k_and_empty_cases():
    st = HitStore([hit(i, body="x" * 900) for i in range(30)])
    r = await recall(RecallRequest("what orbits the sun", k=50, max_chars=1500), store=st)
    assert len(r.prompt_block) <= 1500 and len(r.items) == 2 and st.seen[0][3] == 60
    assert all(len(i.text) <= 600 for i in r.items) and "verified knowledge" in r.prompt_block
    assert (await recall(RecallRequest("   "), store=st)).items == ()
    none = await recall(RecallRequest("x"), store=HitStore([hit(0, "hypothesis")]))
    assert none.prompt_block == "" and none.withheld == 1


async def test_real_store_snippet_found_hypothesis_withheld(tmp_path):
    mem, sch = store.open_store(tmp_path / "core.db"), FakeScheduler()
    good = "def double(n: int) -> int:\n    return n * 2\n"
    out = await solve(make_task(), llm=FakeLLM([{"files": [{"path": "solution.py", "content": good}]}], scheduler=sch),
                      sandbox=FakeSandbox(["pass"]), store=mem, scheduler=sch, visible={"tests/t.py": "x"})
    assert out.snippet_id
    await mem.put(KnowledgeItem("k_h", "fact", "hu", "double hipotézis", "double talán triple"),
                  [Provenance("derived_from", "source", "src_teszt")])
    r = await recall(RecallRequest("double"), store=mem, scope=GUEST)
    assert [i.item_type for i in r.items] == ["snippet"] and "return n * 2" in r.items[0].text
    assert r.withheld >= 1 and "double talán" not in r.prompt_block
