"""Seed migration (01/03 §7.1): the web BRAIN's curated seeds → Core T0 knowledge.

    python -m auri_core migrate-seeds [--dry-run] [--json FILE]

1. export: esbuild (from web/node_modules) bundles a tiny entry that imports the seed modules and
   prints them as JSON. `web/**` is only READ; the bundle lives in a temp dir.
2. import: every item through the store (→ privacy gate), provenance `derived_from seed <file#key>`.
   Definitions / Q→A / doc links: `verified`, trust 0.7 (curated, estimate). Code (snippets, recipes):
   `hypothesis` until a nightly job writes a green test for them. Stable ids → re-running is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..config import CORE_ROOT, load_config
from ..privacy import PrivacyError

WEB = CORE_ROOT.parent / "web"
SEED_DIR = WEB / "src" / "brain" / "seed"
CURATED_TRUST = 0.7
CODE_TRUST = 0.3

_ENTRY = """
import { KNOWLEDGE } from './knowledge';
import { PROGRAMMING_SNIPPETS, PROGRAMMING_QA } from './programmingCurated';
import { WEB_RECIPES } from './recipes';
import { SOURCES } from './sources';
console.log(JSON.stringify({ KNOWLEDGE, PROGRAMMING_SNIPPETS, PROGRAMMING_QA, WEB_RECIPES, SOURCES }));
"""


def export_seeds() -> dict[str, list[dict[str, Any]]]:
    esbuild = WEB / "node_modules" / ".bin" / "esbuild.cmd"
    if not esbuild.exists():
        raise SystemExit("hiányzik a web/node_modules (esbuild) — futtasd a web mappában: npm install")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "seeds.mjs"
        # entry via stdin, cwd = seed dir → relative imports resolve there; nothing is written into web/
        subprocess.run([str(esbuild), "--bundle", "--platform=node", "--format=esm", "--loader=ts", "--log-level=error",
                        f"--outfile={out}"], input=_ENTRY.encode(), check=True, cwd=SEED_DIR)
        res = subprocess.run(["node", str(out)], check=True, capture_output=True, cwd=tmp)
    return json.loads(res.stdout.decode("utf-8"))


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "x"


def build_items(seeds: dict[str, list[dict[str, Any]]]) -> list[tuple[dict[str, Any], str]]:
    """(item, provenance ref_id) pairs, in a stable order with stable ids."""
    items: list[tuple[dict[str, Any], str]] = []
    for e in seeds.get("KNOWLEDGE", []):
        kw = ", ".join(e.get("keywords", []))
        for lang in ("hu", "en"):
            text = (e.get(lang) or "").strip()
            if text:
                items.append(({"id": f"seed_k_{_slug(e['topic'])}_{lang}", "kind": "definition", "lang": lang,
                               "title": e["topic"].replace("-", " "), "body": f"{text}\n\nKulcsszavak: {kw}",
                               "topic": e["topic"], "status": "verified", "trust": CURATED_TRUST, "verification": "curated"},
                              f"knowledge.ts#{e['topic']}"))
    for i, q in enumerate(seeds.get("PROGRAMMING_QA", [])):
        items.append(({"id": f"seed_qa_{i:03d}_{_slug(q['q'])[:40]}", "kind": "qa", "lang": q.get("tech", "en"),
                       "title": q["q"], "body": q["a"], "topic": q.get("tech"), "status": "verified",
                       "trust": CURATED_TRUST, "verification": "curated"}, f"programmingCurated.ts#qa{i}"))
    for s in seeds.get("SOURCES", []):
        items.append(({"id": f"seed_src_{_slug(s['tech'])}_{_slug(s['title'])}", "kind": "source", "lang": "en",
                       "title": s["title"], "body": f"{s['url']}\n\nTémák: {', '.join(s.get('topics', []))}",
                       "topic": s["tech"], "status": "verified", "trust": CURATED_TRUST, "verification": "curated"},
                      f"sources.ts#{s['url']}"))
    for s in seeds.get("PROGRAMMING_SNIPPETS", []):
        items.append(({"id": f"seed_snip_{_slug(s['tech'])}_{_slug(s['title'])}", "kind": "code", "lang": s["tech"],
                       "title": s["title"], "body": f"```{s['tech']}\n{s['code']}\n```\n\nForrás: {s.get('source', '')}",
                       "topic": s["tech"], "status": "hypothesis", "trust": CODE_TRUST}, f"programmingCurated.ts#{s['title']}"))
    for r in seeds.get("WEB_RECIPES", []):
        files = "\n\n".join(f"// {f['name']}\n{f['code']}" for f in r.get("files", []))
        steps = "\n".join(f"- {x}" for x in r.get("steps", []))
        items.append(({"id": f"seed_recipe_{_slug(r['id'])}", "kind": "recipe", "lang": "en", "title": r["title"],
                       "body": f"{r.get('summary', '')}\n\n{steps}\n\n{files}", "topic": r.get("stack"),
                       "status": "hypothesis", "trust": CODE_TRUST}, f"recipes.ts#{r['id']}"))
    return items


async def import_items(store: Any, items: list[tuple[dict[str, Any], str]]) -> dict[str, Any]:
    added = skipped = 0
    rejected: list[str] = []
    for item, ref in items:
        if store.db.execute("SELECT 1 FROM knowledge_items WHERE id = ?", (item["id"],)).fetchone():
            skipped += 1
            continue
        try:
            await store.put(item, [{"relation": "derived_from", "ref_type": "seed", "ref_id": ref}])
            added += 1
        except PrivacyError as e:  # a seed that looks personal stays out of T0 (only its id is reported)
            rejected.append(f"{item['id']}: {e.field}")
    return {"added": added, "skipped": skipped, "rejected": rejected}


def main_migrate_seeds(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="auri_core migrate-seeds")
    ap.add_argument("--dry-run", action="store_true", help="csak export + számlálás, írás nélkül")
    ap.add_argument("--json", type=Path, help="kész export-JSON használata az esbuild helyett")
    a = ap.parse_args(argv)
    seeds = json.loads(a.json.read_text("utf-8")) if a.json else export_seeds()
    items = build_items(seeds)
    by_kind: dict[str, int] = {}
    for it, _ in items:
        by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
    print(f"Seed-export: {len(seeds.get('KNOWLEDGE', []))} téma → {len(items)} elem {by_kind}")
    if a.dry_run:
        return 0
    from ..store import open_store

    store = open_store(load_config().db_path)
    try:
        res = asyncio.run(import_items(store, items))
        print(f"Import: {res['added']} új, {res['skipped']} már megvolt, {len(res['rejected'])} elutasítva (adatvédelem)")
        for r in res["rejected"]:
            print(f"  elutasítva: {r}")
        print(f"Tár: {store.counts()}")
    finally:
        store.close()
    return 0
