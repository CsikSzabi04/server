# A tudás ellenőrzése — mikor lesz egy jelöltből tudás

> **Miről szól:** milyen bizonyítékkal lép elő egy jelölt „hipotézisből” ellenőrzött tudássá:
> kódfuttatás, futtatható állítás, több forrás egyezése, önkonzisztencia, Kritikus, kvíz. Hogyan
> számolunk bizalmi pontszámot, és mi a karantén szabálya. Fázisok: P0 (futtatás), P2 (források),
> P3 (Kritikus), P4 (kvíz, ismétlés).

## 1. Állapotok

```
 jelölt ──canLearn()──▶ hypothesis ──(elég bizonyíték)──▶ verified ──(ismétlés elbukik / ellentmondás)──▶ contested
                           │                                  │
                           │ 30 nap után sincs bizonyíték      └──(TTL lejár, nincs újraellenőrzés)──▶ stale
                           ▼
                        rejected (csak számláló + ok marad)
```

A `contested`, `stale` és az ismétlés részletei: [03-ismetles-felejtes-konszolidacio.md](03-ismetles-felejtes-konszolidacio.md).

## 2. Ellenőrzési módszerek

A súlyok **tervezési kiindulóértékek (becslés)**, a 10-es mappa mérései alapján hangoljuk.

| Módszer (`Evidence.kind`) | Mit bizonyít | Súly | Költség | Mire jó |
|---|---|---|---|---|
| `code-run` | a kód a tesztekkel zöld a sandboxban | 0,9 | sandbox, másodpercek | snippet, error-fix, futtatható állítás |
| `official-doc` | hivatalos (`domainTrust` = 1) forrás szövege alátámasztja | 0,8 | 1 letöltés | api-note, fact |
| `cross-source` | ≥ 2 független domain ugyanazt állítja | 0,6 | 2+ letöltés + összevetés | fact, api-note |
| `user-confirmed` | a felhasználó megerősítette (csak általános tudásnál) | 0,5 | 0 | bármi |
| `critic` | a Kritikus szerep nem talált hibát | 0,25 | 1 modellhívás | bármi |
| `self-consistency` | k független minta ugyanazt mondja | 0,2 | k modellhívás | fact |
| `quiz` | későbbi zárt könyves kvízen helyes | 0,2 | 1–2 hívás | fact, lesson |

A `critic` és a `self-consistency` gyenge: ugyanaz a kis modell **ugyanúgy téved** (korrelált hibák).
Ezért szabály: **csak modellből származó bizonyítékkal semmi nem lehet `verified`**.

## 3. Bizalmi pontszám

```ts
interface Evidence { kind: EvidenceKind; ok: boolean; at: string; detail: string; runtime?: string }

function confidence(baseTrust: number, ev: Evidence[]): number {
  let miss = 1 - baseTrust;                       // „noisy-OR”: független jelek kombinálása
  for (const e of ev) if (e.ok) miss *= 1 - W[e.kind];
  let c = 1 - miss;
  for (const e of ev) if (!e.ok) c *= e.kind === 'code-run' ? 0.1 : 0.6;   // a futtatási bukás szinte vétó
  return Math.round(c * 100) / 100;
}

const EXTERNAL = new Set(['code-run', 'official-doc', 'cross-source', 'user-confirmed']);
function decide(c: number, ev: Evidence[]): 'verified' | 'hypothesis' | 'rejected' {
  if (c < 0.3) return 'rejected';
  if (c >= 0.75 && ev.some((e) => e.ok && EXTERNAL.has(e.kind))) return 'verified';
  return 'hypothesis'; // karantén
}
```

| Példa | Számítás | Eredmény |
|---|---|---|
| Modellválasz (0,3) + Kritikus + önkonzisztencia | 1 − 0,7·0,75·0,8 = 0,58 | karantén (nincs külső bizonyíték) |
| Webes állítás (0,4) + kereszt-forrás | 1 − 0,6·0,4 = 0,76 | ellenőrzött |
| Modell által írt snippet (0,3) + zöld tesztek | 1 − 0,7·0,1 = 0,93 | ellenőrzött |
| Ugyanez, de a tesztek pirosak | 0,3 · 0,1 = 0,03 | elvetve (a kudarc `error-fix` jelölt lehet) |

## 4. Futtatható állítás — a legerősebb eszköz a programozásban

Sok API-állítás átírható egy pici, a sandboxban futó ellenőrzéssé:

```python
# Állítás: „Pythonban a sorted() stabil: egyenlő kulcsnál megtartja az eredeti sorrendet.”
pairs = [(1, "b"), (0, "x"), (1, "a")]
assert sorted(pairs, key=lambda p: p[0]) == [(0, "x"), (1, "b"), (1, "a")]
```

```js
// Állítás: „Az Array.prototype.sort() alapból szövegként hasonlít.”
console.assert(JSON.stringify([10, 9, 1].sort()) === '[1,10,9]');
```

Folyamat: a **Tesztelő** megírja az ellenőrzést → a **Kritikus** megnézi, hogy tényleg az állítást
vizsgálja-e (nem `assert True`, nem a saját kimenetét hasonlítja önmagához) → sandbox, rögzített
futtatókörnyezettel → az `Evidence.runtime` mezőbe kerül a verzió (pl. `python 3.12.x`), ez lesz a
`scope.checkedWith`. Korlát: a zöld ellenőrzés csak azt bizonyítja, amit vizsgál.

## 5. Több forrás egyezése

- **Független** = különböző domain, és a két szöveg nem másolat (ha a kivonatok Jaccard-hasonlósága
  ≥ 0,82 a `dedup.ts` szerint, egy forrásnak számít).
- Elég: egy hivatalos forrás (`official-doc`), vagy két ismert (0,65) forrás, vagy egy ismert és
  két ismeretlen. Csak ismeretlen (0,4) források: legfeljebb karantén.
- Összevetés: mindkét forrásból ugyanabba a rögzített JSON-sémába vonjuk ki az állítást
  (`{subject, property, value, version}`); szám, verzió és név **pontosan** egyezzen.

## 6. Önkonzisztencia és Kritikus

- k = 3 minta, `temperature` 0,7 (becslés); egyezés normalizált összevetéssel.
- Költség a mért `gemma4:e2b` sebességgel (~6,2 tok/s): 3 × 150 token ≈ 75 s (számított becslés)
  → **csak éjszakai ablakban** ([02-ejszakai-onallo-tanulas.md](02-ejszakai-onallo-tanulas.md)).
- A szerepek és promptjaik: [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md).

## 7. Kvíz magadnak

Minden ellenőrzött `fact`/`lesson` elemhez 1–2 kérdés készül. Ismétléskor kétszer válaszol a modell:
**zárt könyvvel** (az elem nélkül) és **nyitott könyvvel** (az elemmel a promptban).

| Zárt | Nyitott | Jelentés | Teendő |
|---|---|---|---|
| jó | jó | a modell már tudja | az elemet ritkábban tesszük a promptba (token-spórolás) |
| rossz | jó | **az elem értékes** | `strength` +1, marad |
| bármi | rossz | az elem homályos vagy hibás | `contested`, újraellenőrzés |

## 8. Minimális bizonyíték fajtánként

| Fajta | Kell a `verified`-hez |
|---|---|
| `snippet` | `code-run` zöld (a saját és a generált tesztekkel) |
| `error-fix` | a hiba reprodukálva **és** a javítás zöld |
| `api-note` | `official-doc` vagy futtatható állítás |
| `fact` | `cross-source` vagy `official-doc` |
| `lesson` | legalább 3 hivatkozott eset + `critic` |

## 9. A karantén szabályai

- Karanténos elem **soha nem hangzik el tényként**. Tervezéskor használható, de „feltételezés”
  címkével, és a terv ellenőrzési pontot kap rá.
- 30 nap után (becslés) ellenőrzés nélkül → `rejected`. Méretkorlát pl. 2000 elem; ha betelik, a
  legkisebb prioritású régi elemek esnek ki.
- A felhasználó a BRAIN-nézetben látja a karantént, és megerősíthet vagy elvethet elemeket.

## Kész, ha

- `decide()` egységtesztje lefedi a 3. pont táblázatát, és bizonyítja: modell-only bizonyíték soha
  nem ad `verified`-et;
- P0-ban minden tárolt snippetnek van zöld `code-run` bizonyítéka a futtatókörnyezet verziójával;
- havi szúrópróba: 20 véletlen `verified` elemből kézzel ellenőrizve legalább 19 helyes (mérőszám:
  [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md));
- a karanténban nincs 30 napnál régebbi elem.

## Kapcsolódó

- [01-tanulasi-forrasok.md](01-tanulasi-forrasok.md) · [03-ismetles-felejtes-konszolidacio.md](03-ismetles-felejtes-konszolidacio.md) · [05-mit-nem-szabad-megtanulni.md](05-mit-nem-szabad-megtanulni.md)
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) · [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md)
- [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) · [../02-belso-parbeszed/02-vita-protokoll.md](../02-belso-parbeszed/02-vita-protokoll.md)
