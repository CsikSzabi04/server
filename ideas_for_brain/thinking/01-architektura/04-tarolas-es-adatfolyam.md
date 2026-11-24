# Tárolás és adatfolyam

> **Miről szól:** az Auri Core általános tudástárának (`core.db`, T0) SQLite-sémavázlata —
> tudáselemek, kódrészletek tesztekkel, források bizalommal, epizódok és tanulságok, beágyazások
> (`embeddinggemma`), teljes szöveges keresés (FTS5), eredet (provenance) — és a fő adatfolyamok.

## 1. Elvek

1. **Nincs eredet nélküli tudás.** Minden elemhez legalább egy `provenance` sor tartozik (forrás,
   epizód, modell, felhasználói visszajelzés vagy seed).
2. **Státusz mindenen** (a közös, végleges lista): `hypothesis` (= karantén) → `verified` → `stale` /
   `contested` / `refuted`; a régóta nem használt elem `archived` (nem törlődik). A modell-kimenet önmagában
   soha nem `verified` ([../00-alapok/02-oszinte-korlatok.md](../00-alapok/02-oszinte-korlatok.md)).
3. **Szintenként külön fájl:** `core.db` = T0 (általános, személyes adat nélkül); a T1 a
   `users/<hash>.db`-ben ugyanilyen sémával ([03-hol-fut-auri-core.md](03-hol-fut-auri-core.md)).
   Minden írás előtt az Adatvédelmi kapu fut — az epizódok `goal` mezőjére is.
4. **Epizód csak hozzáfűzéssel** íródik (napló), a tudáselemek frissülhetnek.
5. **SQLite WAL + FTS5**, mint a Jarvis `memory/store.py`-ban; ékezettűrő tokenizáló.

## 2. Sémavázlat

```sql
CREATE TABLE knowledge_items (                       -- tények, fogalmak, how-to, Q→A, összefoglalók
  id TEXT PRIMARY KEY, kind TEXT NOT NULL,           -- fact|concept|howto|qa|summary
  lang TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'hypothesis',         -- hypothesis|verified|contested|stale|refuted|archived
  verification TEXT,                                 -- tests_passed|multi_source|user_confirmed|curated|critic_ok
  trust REAL NOT NULL DEFAULT 0.3,                   -- 0..1
  topic TEXT, tags TEXT, version_tag TEXT,           -- version_tag pl. 'python>=3.11', 'react@19'
  ttl_days INTEGER,                                  -- NULL = nem jár le
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, verified_at TEXT,
  uses INTEGER NOT NULL DEFAULT 0, last_used_at TEXT);

CREATE TABLE code_snippets (
  id TEXT PRIMARY KEY, language TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
  code TEXT NOT NULL, entrypoint TEXT, deps TEXT,    -- deps: JSON-tömb
  license TEXT NOT NULL,                             -- own|MIT|Apache-2.0|… (ismeretlen → nem tároljuk)
  status TEXT NOT NULL DEFAULT 'hypothesis', trust REAL NOT NULL DEFAULT 0.3,
  version_tag TEXT, task_signature TEXT,             -- a feladat normalizált lenyomata (cache-kulcs)
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, verified_at TEXT, uses INTEGER NOT NULL DEFAULT 0);

CREATE TABLE snippet_tests (
  id TEXT PRIMARY KEY, snippet_id TEXT NOT NULL REFERENCES code_snippets(id) ON DELETE CASCADE,
  framework TEXT NOT NULL,                           -- pytest|vitest|node:test
  test_code TEXT NOT NULL, locked INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT, last_result TEXT,                -- pass|fail|error
  passed INTEGER, total INTEGER, runtime_ms INTEGER, env TEXT);   -- env: JSON (python/node verzió)

CREATE TABLE sources (
  id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, domain TEXT NOT NULL, title TEXT,
  fetched_at TEXT NOT NULL, content_hash TEXT, license TEXT,
  trust REAL NOT NULL, trust_reasons TEXT);          -- JSON: ["official_docs","agrees_with:src_12"]

CREATE TABLE provenance (
  item_type TEXT NOT NULL, item_id TEXT NOT NULL,    -- knowledge|snippet|lesson
  relation TEXT NOT NULL,                            -- derived_from|verified_by|contradicted_by|generated_by
  ref_type TEXT NOT NULL, ref_id TEXT NOT NULL,      -- source|episode|model|feedback|seed|cloud
  created_at TEXT NOT NULL,
  PRIMARY KEY (item_type, item_id, relation, ref_type, ref_id));

CREATE TABLE episodes (
  id TEXT PRIMARY KEY, mode TEXT NOT NULL, origin TEXT NOT NULL,  -- origin: user|selfstudy|system
  goal TEXT NOT NULL, outcome TEXT NOT NULL,         -- DONE|GIVE_UP|ASK_USER|CANCELLED|PAUSED
  level_start INTEGER, level_end INTEGER, llm_calls INTEGER, out_tokens INTEGER, wall_ms INTEGER,
  repair_rounds INTEGER, predicted_success REAL, started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE episode_steps (
  episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE, seq INTEGER NOT NULL,
  state TEXT NOT NULL, model TEXT, prompt_hash TEXT, out_tokens INTEGER, ms INTEGER,
  verdict TEXT, signature TEXT, PRIMARY KEY (episode_id, seq));
CREATE TABLE lessons (
  id TEXT PRIMARY KEY, episode_id TEXT REFERENCES episodes(id), text TEXT NOT NULL, tags TEXT,
  success INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0, helped INTEGER NOT NULL DEFAULT 0);

CREATE TABLE embeddings (
  item_type TEXT NOT NULL, item_id TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL,
  vec BLOB NOT NULL, text_hash TEXT NOT NULL,        -- text_hash: újraszámolás, ha a szöveg változik
  PRIMARY KEY (item_type, item_id, model));

CREATE VIRTUAL TABLE knowledge_fts USING fts5(title, body, content='knowledge_items',
  tokenize='unicode61 remove_diacritics 2');         -- „arvizturo” is megtalálja az „árvíztűrő”-t
CREATE VIRTUAL TABLE snippet_fts USING fts5(title, description, code, content='code_snippets',
  tokenize='unicode61 remove_diacritics 2');

CREATE TABLE jobs (                                  -- az Ütemező tartós sora (háttér, hosszú feladat)
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, priority INTEGER NOT NULL, state TEXT NOT NULL,
  payload TEXT NOT NULL, checkpoint TEXT, not_before TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);   -- pl. schema_version
-- cache_entries: ld. 08-modellek-es-utvonalvalasztas/04 · study_items (ismétlés): ld. 05-tanulas/03
```

Az FTS-táblákat triggerek tartják szinkronban (a szokásos `AFTER INSERT/UPDATE/DELETE` minta).

## 3. Keresés: FTS5 + beágyazás

```python
STATUS_WEIGHT = {"verified": 1.0, "hypothesis": 0.4, "contested": 0.2, "stale": 0.2}  # refuted, archived: kiszűrve

def search(q: str, kinds: set[str], k: int = 8) -> list[Hit]:
    lexical = fts_bm25(q, kinds, limit=50)                 # szó szerinti (ékezettűrő)
    vec = embedder.embed(q)                                # None, ha az embeddinggemma nem elérhető
    semantic = top_cosine(vec, kinds, limit=50) if vec is not None else []
    fused = reciprocal_rank_fusion([lexical, semantic], k=60)
    return sorted(fused, key=lambda h: h.rrf * h.trust * freshness(h) * STATUS_WEIGHT[h.status],
                  reverse=True)[:k]
```

- A beágyazás opcionális (a Jarvis `embed.py` mintája): hiba vagy időtúllépés → csak FTS, lassulás nélkül.
- Vektorok: `float32` BLOB. Eleinte a memóriában tartott mátrixon numpy-val, teljes összevetéssel;
  ha az elemszám ezt lassúvá teszi (> ~50 ezer, becslés), `sqlite-vec` vagy kisebb dimenzió (mérni kell).
- `embeddinggemma` ~0,6 GB RAM, rövid `keep_alive`, hogy ne foglalja a helyet a fő modell elől.

## 4. Státuszátmenetek

| Honnan → hová | Kiváltó ok |
|---|---|
| (új) → `hypothesis` | modell-kimenet, web-kivonat, `POST /learn`, import |
| `hypothesis` → `verified` | zöld, zárolt tesztek · ≥ 2 független, megbízható forrás egyezik · a felhasználó megerősíti · kurált seed |
| `verified` → `stale` | lejárt TTL · elavult `version_tag` · ismétléskor a teszt környezeti okból nem fut |
| `stale` → `verified` | sikeres újraellenőrzés |
| `verified` → `contested` | ismétléskor elbukik, vagy egyenrangú források ellentmondanak, de a hiba nem bizonyított ([../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md)) |
| `contested` → `verified` / `refuted` | az újraellenőrzés eldönti |
| bármely → `refuted` | ugyanabban a környezetben bukó teszt · megbízhatóbb forrás ellentmond · a felhasználó javítja |
| `verified` / `stale` → `archived` | a hasznossági óra lejár (soha nem használt); visszahozható újraellenőrzéssel |
| `refuted` → (törlés) | konszolidációkor, 30 nap után (becslés); a tanulság és az eredet-sor marad |

## 5. Adatfolyamok

```
A) Kérdés (chat):  API → kapu (tier) → search() → [ellenőrzött, friss? → válasz] → modell fogalmaz a
                   találatokból → válasz + források → epizód (anonim) → visszajelzés → trust ±
B) Kód (P0):       API → ciklus → tesztek (zárolva) + kód → sandbox → zöld → code_snippets +
                   snippet_tests + provenance(verified_by episode) + lesson + embeddings
C) Web (P2):       keresés → sources(trust) → kivonat → knowledge_items(hypothesis) +
                   provenance(derived_from source) → 2. független forrás egyezik → verified
D) Éjszaka (P4):   jobs → tesztek újrafuttatása (stale/refuted/verified) → konszolidáció
                   (cosine > 0,9 → összevonás, mint a Jarvis memóriájában) → hiánylista → tananyag
```

## 6. Méretbecslés (becslés)

10 ezer tudáselem (~1 KB) + 10 ezer kódrészlet tesztekkel (~3 KB) + 20 ezer 768 dimenziós
`float32` vektor (~3 KB/db) ≈ 10 + 30 + 60 ≈ **100 MB**. Egy SQLite-fájlnak ez kényelmes; az
epizódnaplót negyedévente összesíteni lehet (a lépések törölhetők, az összesítés marad).
(A 768-as dimenzió az `embeddinggemma` leírásából való — a telepítésnél ellenőrizni kell.)

## 7. Kész, ha

- A séma migrációs szkripttel jön létre (`schema_version` a `meta` táblában), idempotensen.
- Eredet nélküli elemet az API nem enged beírni (teszt); `generated_by model` egymagában nem lehet `verified`.
- Az „árvíztűrő” keresés megtalálja az ékezet nélkül tárolt elemet és fordítva (FTS-teszt).
- Beágyazás nélkül (Ollama leállítva) a keresés FTS-sel működik tovább (teszt).

## Kapcsolódó

- [01-attekintes.md](01-attekintes.md) — a Memória/Tudástár felelőssége
- [02-gondolkodo-ciklus.md](02-gondolkodo-ciklus.md) — epizódok, `jobs.checkpoint`
- [03-hol-fut-auri-core.md](03-hol-fut-auri-core.md) — T0 / T1 / T2
- [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) — a `sources.trust` számítása
- [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md) — ismétlés, összevonás
- [../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md) — mi nem kerülhet be
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) — a kódrészletek használata
- [../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md) — `cache_entries`
