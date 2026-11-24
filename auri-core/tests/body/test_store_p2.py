"""AI-3 for AI-1's P2/P6 requests: provenance(), put_source(), SQLite search cache, config, read-only guest store."""

from __future__ import annotations

import pytest

from auri_core.config import build_config
from auri_core.contracts import Provenance
from auri_core.research.types import SearchResult
from auri_core.server.app import ReadOnlyStore
from auri_core.store import SqliteKnowledgeStore, StoreError


async def test_provenance_rows(store):
    kid = await store.put({"title": "t", "body": "b"}, [{"relation": "derived_from", "ref_type": "seed", "ref_id": "x#1"}])
    assert await store.provenance("knowledge", kid) == [Provenance("derived_from", "seed", "x#1")]
    assert await store.provenance("knowledge", "nincs") == []


async def test_put_source_upsert(store):
    url = "https://stackoverflow.com/questions/1234567/how"
    a = await store.put_source(url, title="Q", trust=0.6)
    b = await store.put_source(url, title="Q2", trust=0.7)
    row = store.db.execute("SELECT domain, title, trust FROM sources WHERE id=?", (a,)).fetchone()
    assert a == b and tuple(row) == ("stackoverflow.com", "Q2", 0.7)
    with pytest.raises(StoreError):
        await store.put_source("file:///etc/passwd")


def test_search_cache_persists(tmp_path):
    t = [1000.0]
    s = SqliteKnowledgeStore(tmp_path / "c.db")
    c = s.search_cache(clock=lambda: t[0])
    c.put("Python  list", [SearchResult("Lists", "https://docs.python.org/3/", "x", "ddg")])
    s.close()
    s2 = SqliteKnowledgeStore(tmp_path / "c.db")  # restart: still there, same key normalisation
    c2 = s2.search_cache(clock=lambda: t[0])
    assert c2.get("python list")[0].url == "https://docs.python.org/3/"
    c2.put("nincs ilyen", [])
    t[0] += 3601
    assert c2.get("nincs ilyen") is None and c2.get("nincs ilyen", allow_stale=True) == []
    s2.close()


def test_config_router_fields():
    cfg = build_config({"AURI_CORE_MODEL_L3": "qwen3.5:9b", "AURI_CORE_CLOUD_MODE": "yolo", "AURI_CORE_RAM_BUDGET_GB": "7"})
    assert cfg.models.l3 == "qwen3.5:9b" and cfg.cloud_mode == "off" and cfg.ram_budget_gb == 7.0
    assert build_config({}).models.l3 is None and build_config({}).cloud_model is None


def test_guest_store_is_read_only(store):
    ro = ReadOnlyStore(store)
    assert hasattr(ro, "search") and hasattr(ro, "provenance")
    assert not hasattr(ro, "put") and not hasattr(ro, "put_snippet") and not hasattr(ro, "record_episode")
