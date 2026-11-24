# Gyakorlófeladatok — generátor, nehézségi lépcső, automatikus értékelés

> **Miről szól:** honnan jönnek a gyakorlófeladatok, hogyan nő a nehézségük, hogyan pontozza őket a gép
> tesztekkel, és hogyan gyakorol Auri éjjel. Teljes példák TypeScriptben és Pythonban (látható és rejtett
> tesztekkel). A feladatformátum közös a mérőkészlettel ([09](09-meres-es-benchmark.md)).

## 1. Feladatformátum (`CodeTask`)

```yaml
id: ts-l1-0007
level: 1                      # L0..L4 (01)
lang: ts                      # ts | py | sql
topics: [ts.strings, x.testing]
title_hu: Magyar slug
prompt_hu: |
  Írj `slugifyHu(s: string): string` függvényt: kisbetűs, ékezetmentes eredmény; a nem betű/szám
  karakterek minden sorozata egyetlen kötőjel; az elején és a végén nincs kötőjel.
signature: "export function slugifyHu(s: string): string"
files: {visible: tests/visible.test.ts, hidden: tests/hidden.test.ts, reference: ref/solution.ts}
source: {kind: own, license: own}   # own | exercism (MIT) | generated
limits: {wall_s: 20, mem_mb: 512}
split: practice               # practice | dev | heldout | regression — a heldout SOHA nem gyakorlás (09)
family: str-normalize         # feladatcsalád (02: exerciseFamilies)
rating: 1180                  # nehézség (3. pont)
```

## 2. Honnan jönnek a feladatok

| Forrás | Hogyan | Minőségkapu |
|---|---|---|
| **A — kurált családok** | kézzel írt sablon + paraméterek (pl. „normalizálj X-et Y szabállyal”), egyszer ellenőrzött referencia-megoldással | a referencia zöld a látható + rejtett teszteken |
| **B — modell által javasolt** | a Tanár szerep feladatot + referenciát + teszteket ír egy gyenge témához | referencia zöld; tesztek **pirosak a csonkon**; mutáns-próba ≥ 60 %; Kritikus: minden rejtett teszt a szöveg egy mondatára vezethető; hasonlóság a meglévőkhöz < 0,9 |
| **C — hibás változatok** | egy T2+ snippetbe szándékos hiba (off-by-one, fordított feltétel) → „keresd meg és javítsd” | az eredeti zöld, a mutáns piros |
| **D — Exercism `problem-specifications`** (MIT) | a kanonikus tesztadatból automatikus TS/Python-teszt, magyarra fordított leírás | a konverzió után a teszteknek van referencia-megoldása |
| **E — saját repóból** ([07](07-sajat-projektekbol-tanulas.md)) | „írj tesztet ehhez a meglévő függvényhez” / „refaktoráld, a tesztek maradjanak zöldek” | csak S1-ben, allowlistes másolaton |

A B-forrás veszélye a **visszhangkamra** (a modell olyat talál ki, amit eleve tud) → a heti mix ≥ 40 %-a A/C/D-forrásból jön (célérték).

## 3. Nehézség és kiválasztás

Témánként Elo-szerű értékelés Aurinak (`R_a`) és minden feladatnak (`R_t`):

```ts
const expected = (Ra: number, Rt: number) => 1 / (1 + 10 ** ((Rt - Ra) / 400));
function update(Ra: number, Rt: number, S: 0 | 0.6 | 1, K = 24) {   // S: 1 = pass@1, 0,6 = javítással, 0 = bukás
  const d = K * (S - expected(Ra, Rt));
  return { Ra: Ra + d, Rt: Rt - d };
}
// kiválasztás: olyan feladat, amire expected ∈ [0,55; 0,80] — „kívánatos nehézség”
```

Kezdőértékek: L0 = 1000, L1 = 1200, L2 = 1400, L3 = 1600, L4 = 1800; a `K` és a sávhatárok is **kalibrálandók** a naplóból.

## 4. Automatikus értékelés

| Összetevő | Súly | Megjegyzés |
|---|---|---|
| rejtett tesztek | 70 % | arányosan; **siker = mind zöld** (ez megy a mérőszámokba) |
| látható tesztek | 10 % | |
| lint- és típustisztaság | 10 % | `tsc --strict`, `ruff` |
| javítási körök | 10 % | 0 kör = teljes, 3 kör = 0 |

A súlyozott pont csak a fejlődési naplóhoz kell ([../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md](../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md));
az Elo és a mérés a bináris sikert használja. A hibakeresési (C) feladatnál plusz feltétel: a diff ≤ 5 sor.

## 5. Példa — TypeScript, L1: `slugifyHu`

```ts
// tests/visible.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slugifyHu } from '../solution.ts';
test('alap', () => assert.equal(slugifyHu('Helló Világ'), 'hello-vilag'));
test('ékezetek', () => assert.equal(slugifyHu('Árvíztűrő tükörfúrógép'), 'arvizturo-tukorfurogep'));
```

```ts
// tests/hidden.test.ts — a modell SOHA nem látja (importok mint fent, plusz: import fc from 'fast-check')
test('üres', () => assert.equal(slugifyHu(''), ''));
test('szélek és ismétlés', () => assert.equal(slugifyHu('  --Több   szóköz!!  '), 'tobb-szokoz'));
test('ő/ű nagybetűvel', () => assert.equal(slugifyHu('ŐŰ őű'), 'ou-ou'));
test('írásjelek', () => assert.equal(slugifyHu('C++ & Node.js 24'), 'c-node-js-24'));
test('idempotens', () => fc.assert(fc.property(fc.string(), (s) => slugifyHu(slugifyHu(s)) === slugifyHu(s))));
```

```ts
// ref/solution.ts — referencia (csak a feladat validálásához)
export function slugifyHu(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
```

## 6. Példa — Python, L1: `parse_forint`

Feladat: `parse_forint(s: str) -> int` — magyar formátumú forintösszeg egész számmá: `"1 234 Ft"` → 1234,
`"12 000 HUF"` → 12000, `"-500 Ft"` → -500; ezreselválasztó lehet szóköz vagy nem törhető szóköz (U+00A0);
érvénytelen bemenetre `ValueError`.

```python
# tests/test_visible.py
from solution import parse_forint

def test_alap():
    assert parse_forint("1 234 Ft") == 1234
    assert parse_forint("12 000 HUF") == 12000
```

```python
# tests/test_hidden.py — csak a specifikációban KIMONDOTT viselkedést ellenőrzi
import pytest
from hypothesis import given, strategies as st
from solution import parse_forint

@pytest.mark.parametrize("s,v", [("-500 Ft", -500), ("1 000 Ft", 1000), ("  7 Ft ", 7)])
def test_ervenyes(s, v):
    assert parse_forint(s) == v

@pytest.mark.parametrize("s", ["abc", "Ft", ""])
def test_ervenytelen(s):
    with pytest.raises(ValueError):
        parse_forint(s)

@given(st.integers(min_value=-10**9, max_value=10**9))
def test_oda_vissza(n):
    assert parse_forint(f"{n:,}".replace(",", " ") + " Ft") == n
```

Tanulság a feladatíráshoz: a `"12,50 Ft"` (tizedes) esetet a leírás nem rendezi → rejtett teszt **nem** kérheti számon.

## 7. További példák (vázlat)

| Id | Szint | Feladat | Amit gyakoroltat |
|---|---|---|---|
| `ts-l2-0003` | L2 | `createRateLimiter({ max, windowMs, now })` → `tryAcquire(key): boolean`, csúszó ablak, **injektált óra** | állapot, idő valódi várakozás nélkül, `Map` |
| `py-l2-0005` | L2 | `Inventory` osztály: `add`, `remove` (saját `OutOfStock` kivétel), `report()` rendezett listát ad | OOP, kivételek, rendezés |
| `sql-l1-0002` | L1 | `diak(id, nev)`, `jegy(diak_id, targy, ertek)`: tárgyankénti átlag 2 tizedesre, csökkenő sorrendben; fixture: „Teszt Elek”, „Minta Máté” | GROUP BY, ROUND, ORDER BY |
| `ts-l1-d-0001` | L1 (C) | hibás `paginate(items, page, size)` (off-by-one) + egy piros teszt → javítás ≤ 5 soros diffel | hibakeresés ([06](06-hibakereses.md)) |
| `ts-l3-0001` | L3 | Express todo API memóriatárral, `GET/POST/PATCH/DELETE`, tesztek a loopbacken | REST, validáció, hibakezelő middleware |

## 8. Éjszakai gyakorlás

Csak tétlenségben/éjjel, egy Ollama-sávval; a felhasználó első mozdulatára **azonnal szünet** ([../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)).

```
1. bemelegítés: az esedékes ismétlések (05-tanulas/03) — 2–3 rövid feladat
2. fő blokk:    70 % aktuális szint · 20 % következő szint · 10 % hibakeresés (C) — Elo szerinti választás
3. zárás:       a napi regressziós minta (09) — 10 feladat, rotálva
4. napló:       siker/bukás, körszám, idő, új tanulságok, Elo-változás; a zöld megoldások → tudástár (03)
```

Időkeret: egy L1-feladat több perc ([05](05-tesztvezerelt-gondolkodas.md) 7. pont) → egy 90 perces ablakba ~10–20 feladat fér (becslés, **mérni kell**).

## 9. Mi kerül a tudástárba — és mi nem

- **Be:** a zöld megoldás a tesztjeivel (T2; tulajdonságteszttel és ≥ 3 bevált felhasználás után T3), a hibakeresési tanulság ([06](06-hibakereses.md) 9. pont).
- **Nem:** a `dev`/`heldout` feladatok megoldásai, a bukott megoldások (csak naplóba), licenc nélküli forrás feladatszövege.

## 10. Kész, ha

- van ≥ 40 kurált feladatcsalád (TS + Python + SQL), mindegyik referenciával, látható és rejtett tesztekkel;
- a B-generátor elutasítja a „zöld a csonkon” és a kétértelmű feladatokat (tesztkészlet fedi);
- az Elo-kiválasztás 2 hét gyakorlás után témánként stabilizálódik (a `R_a` heti ingadozása < 50 pont, célérték);
- az éjszakai napló minden reggel olvasható összefoglalót ad, és a held-out készlet canary-ellenőrzése tiszta ([09](09-meres-es-benchmark.md)).

## Kapcsolódó

- [02-tananyag.md](02-tananyag.md) · [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [09-meres-es-benchmark.md](09-meres-es-benchmark.md)
- [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) · [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md)
- [../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md) · [../12-otlettar/01-otletek.md](../12-otlettar/01-otletek.md)
