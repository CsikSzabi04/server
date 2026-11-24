# Cache és újrahasznosítás

> **Miről szól:** a router L0 szintje — pontos és szemantikus cache, az ellenőrzött válaszok és
> kódmegoldások újrahasznosítása, az érvénytelenítés szabályai, és hogyan mérjük, mennyit spórolunk
> (és mennyit tévedünk) vele. CPU-n minden elkerült modellhívás perceket ér.

## 1. Miért ennyire fontos itt?

Egy kód-feladat a gépen több perc (a `code` keret ~15 perc, becslés; 1000 token kimenet ≈ 2,7 perc a
mért 6,2 tok/s-mal). Egy cache-találat + a tárolt tesztek újrafuttatása másodpercek. A cache tehát
nem kényelmi funkció, hanem a „tapasztalatból okosodás” **gyakorlati formája** — de csak akkor, ha
**ellenőrzött** tudást ad vissza, és ritkán téved.

## 2. Rétegek

| Réteg | Kulcs | Érték | Mikor használható |
|---|---|---|---|
| **C1** pontos | normalizált kérdés (kisbetű, ékezet- és szóköz-normalizálás) + nyelv + mód | ellenőrzött válasz / elem azonosítója | `verified` és friss |
| **C2** szemantikus | `embeddinggemma`-vektor, koszinusz ≥ τ, azonos `kind` és nyelv | ellenőrzött válasz | mint C1 **és** a kulcsentitások egyeznek (3. pont) |
| **C3** kódmegoldás | `task_signature` (függvénynév, be/ki típusok, nyelv, normalizált leírás) + szemantikus egyezés | `code_snippets` + `snippet_tests` | **csak a tárolt tesztek újrafuttatása után**; ha az új kérésnek saját tesztje is van, az is lefut |
| **C4** web | lekérdezés + TTL | találatok, oldal-kivonatok | TTL-ig (a webes `autolearn/searchCache.ts` és `ttlDaysForQuery` mintája) |
| **C5** LLM-hívás | (modell + verzió, prompt-hash, paraméterek) | nyers kimenet | csak determinisztikus lépésnél (`temperature ≤ 0,2`), pl. osztályozás |

Az Ollama KV-cache-e nem a mi rétegünk, de a promptépítés kíméli
([01-helyi-modellek.md](01-helyi-modellek.md), 4. pont).

Szint-szabályok: csak **T0** elem kerül a közös cache-be; a T1 (saját fiók) válaszai legfeljebb a
felhasználó saját `users/<hash>.db`-jében cache-elhetők. Vendég olvashatja a T0 cache-t, írni nem.

## 3. Keresés a cache-ben

```python
TAU = {"chat": 0.92, "code": 0.90, "research": 0.93}      # becslés — kalibrálni kell (5. pont)

async def cache_lookup(goal: Goal) -> CacheHit | None:
    if (e := db.cache_get(exact_key(goal))) and e.valid():                  # C1
        return e.hit("exact")
    vec = embedder.embed(goal.text)
    if vec is None:                                                          # nincs beágyazás → nincs C2/C3
        return None
    for c in db.semantic_candidates(vec, kind=goal.kind, lang=goal.lang, top=5):
        if c.cosine < TAU[goal.kind] or not c.verified_fresh():
            continue
        if key_entities(goal.text) != key_entities(c.query):               # a „majdnem ugyanaz” csapda
            continue
        if goal.kind == "code" and not await verifier.rerun(c.snippet_id, env=current_env()):   # C3
            await store.demote(c.snippet_id, "rerun_failed")
            continue
        return c.hit("semantic")
    return None
```

**Kulcsentitások** (a hamis találat fő oka, hogy két kérdés hasonló, de egy apróságban más):
számok és mértékegységek, verziók (`python 3.11` ≠ `3.12`), azonosítók (`camelCase`, `snake_case`),
nyelv- és könyvtárnevek, tagadás („nem”, „ne”, „nélkül”, `without`), irány („növekvő” ≠ „csökkenő”).
Ha ezek halmaza eltér, nincs találat — akármilyen magas a koszinusz.

## 4. Érvénytelenítés

| Esemény | Hatás |
|---|---|
| Lejár a TTL (témától függ: hír ~1 nap, könyvtár-API ~30–90 nap, alapfogalom nem jár le — becslés) | a bejegyzés érvénytelen, az elem `stale` |
| Az alapul szolgáló elem `stale` vagy `refuted` lesz | **minden** függő bejegyzés érvénytelen (`cache_deps`) |
| Modell- vagy prompt-sablon verzióváltás | C5 bejegyzések érvénytelenek (a kulcs része a verzió) |
| A felhasználó rossznak jelöli vagy kijavítja | bejegyzés érvénytelen, az elem bizalma csökken, a javítás új hipotézis |
| A C3 újrafuttatás bukik | a kódrészlet `stale` (környezeti ok) vagy `refuted` (ugyanabban a környezetben) |
| Python/Node főverzió-váltás | a C3 `env`-egyezést kér; eltérésnél kötelező újrafuttatás |
| A mintavételes audit hamis találatot talál | az adott `kind` τ-ja emelkedik |

```sql
CREATE TABLE cache_entries (
  key TEXT PRIMARY KEY, layer TEXT NOT NULL,          -- exact|semantic|llm
  kind TEXT NOT NULL, lang TEXT, query_norm TEXT NOT NULL,
  answer_ref TEXT NOT NULL,                           -- knowledge / snippet / llm-kimenet azonosító
  model_version TEXT, created_at TEXT NOT NULL, valid_until TEXT,
  hits INTEGER NOT NULL DEFAULT 0, last_hit_at TEXT, invalidated_reason TEXT);
CREATE TABLE cache_deps (                             -- melyik bejegyzés melyik elemre épül
  key TEXT NOT NULL, item_type TEXT NOT NULL, item_id TEXT NOT NULL,
  PRIMARY KEY (key, item_type, item_id));
```

## 5. A megtakarítás és a tévedés mérése

| Mérőszám | Hogyan számoljuk | Cél (becslés) |
|---|---|---|
| Találati arány rétegenként | találatok / kérések, C1–C5 külön | nőjön hétről hétre |
| Megtakarított LLM-idő | Σ (az adott `kind` medián ciklusideje a **saját** epizódokból − a cache-válasz ideje) | nőjön |
| Hamis találati arány | heti mintavétel (pl. 20 szemantikus találat, kézi vagy Kritikus-ellenőrzés) + rossznak jelölt cache-válaszok | ≤ 2% |
| Elavult találat | a C3 újrafuttatások bukásaránya | csökkenjen |
| Felhőfüggőség | L4-et használó sikeres epizódok aránya | csökkenjen ([03-felhos-segitseg-opcionalis.md](03-felhos-segitseg-opcionalis.md)) |

**τ kalibrálása:** egy kis, kézzel címkézett párkészlet (hasonló / nem hasonló kérdéspárok magyarul és
angolul, fiktív adatokkal) → minden `kind`-ra az a legkisebb τ, amelynél a hamis találat ≤ 2%. A
párkészlet az értékelő készletek része ([../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)).

## 6. Kész, ha

- Ugyanaz a P0-feladat másodszor C1/C3 találat: modellhívás nélkül, a tárolt tesztek újrafuttatásával
  (mérve az epizódnaplóban: `llm_calls = 0`).
- Entitás-tesztek: „rendezd növekvő sorrendbe” ≠ „rendezd csökkenő sorrendbe”, „python 3.11” ≠
  „python 3.12” — egyik sem ad találatot a másikra.
- Egy elem `refuted`-ra állítása után az összes ráépülő bejegyzés érvénytelen (teszt).
- A `GET /stats` mutatja a találati arányokat és a becsült megtakarított LLM-időt.

## Kapcsolódó

- [02-router.md](02-router.md) — L0 a szintek között
- [01-helyi-modellek.md](01-helyi-modellek.md) — a modellhívás ára
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) — státuszok, `code_snippets`, beágyazások
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) — a kódtudástár
- [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md) — tesztek éjszakai újrafuttatása
- [../03-web-szorfozes/04-tanulas-a-webbol.md](../03-web-szorfozes/04-tanulas-a-webbol.md) — a webes TTL
- [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md) — mérőszámok
