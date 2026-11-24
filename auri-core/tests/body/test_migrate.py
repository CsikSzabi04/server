"""AI-3 P1: seed migration — curated → verified, code → hypothesis, idempotent, privacy-gated."""

from __future__ import annotations

from auri_core.migrate.seeds import build_items, import_items

SEEDS = {
    "KNOWLEDGE": [
        {"topic": "gravity", "keywords": ["gravity", "gravitáció"], "en": "Gravity pulls objects together.",
         "hu": "A gravitáció a testeket egymás felé húzza."},
        {"topic": "teszt-elek", "keywords": [], "en": "", "hu": "Teszt Elek, 1990.01.01"},
    ],
    "PROGRAMMING_QA": [{"tech": "css", "q": "how to center a div", "a": "display:flex; align-items:center;"}],
    "PROGRAMMING_SNIPPETS": [{"tech": "css", "title": "Center a div", "code": ".box { display: flex; }", "source": "https://x"}],
    "WEB_RECIPES": [],
    "SOURCES": [{"tech": "python", "title": "Python docs", "url": "https://docs.python.org/3/", "topics": ["stdlib"]}],
}


async def test_seed_import(store):
    items = build_items(SEEDS)
    res = await import_items(store, items)
    assert res["added"] == 5 and res["rejected"] == ["seed_k_teszt-elek_hu: body"]
    assert (await import_items(store, items))["skipped"] == 5  # re-run is a no-op
    hits = await store.recall("gravitacio")
    assert hits and hits[0]["status"] == "verified" and hits[0]["sources"][0]["ref_id"] == "knowledge.ts#gravity"
    code = store.db.execute("SELECT status FROM knowledge_items WHERE kind = 'code'").fetchone()[0]
    assert code == "hypothesis"
    assert await store.recall("center div") and all(h["status"] == "verified" for h in await store.recall("center div"))


def test_reserved_doc_addresses_not_personal():
    from auri_core import privacy

    assert not privacy.is_personal("INSERT INTO users VALUES ('ann@example.com')", kind="code")
    assert not privacy.is_personal("ssh user@192.0.2.10", kind="code")
    assert privacy.is_personal("írj ide: teszt.elek@gmail.com")
    assert privacy.is_personal("ann@example.com és teszt.elek@freemail.hu", kind="code")


async def test_recall_one_language_per_topic(store):
    await import_items(store, build_items(SEEDS))
    hu = await store.recall("gravity", lang="hu")
    assert len([h for h in hu if h["title"] == "gravity"]) == 1 and hu[0]["id"].endswith("_hu")
    assert (await store.recall("gravity", lang="en"))[0]["id"].endswith("_en")
