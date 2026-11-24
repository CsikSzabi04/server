# Mit mérünk — a fejlődés mérőszámai

> **Miről szól:** azok a számok, amelyekből kiderül, hogy az agy tényleg jobb lett-e: kódsikerességi
> arányok, válaszhelyesség, tudásminőség, cache- és agy-találati arány, elkerült felhőhívások,
> késleltetés, biztonsági nullák és regressziók. Mindegyiknél: definíció, készlet, alapérték, cél.

## 1. Elvek

- **Ami nem mérhető, arról nem állítjuk, hogy javult** ([../thinking.md](../thinking.md), 5. vezérelv).
- Alapérték csak **mért** szám lehet (forrás: [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
  vagy egy futtatott kiértékelés). Ahol még nincs: „még nincs”. A célok **becslések**, az első mért
  alapérték után rögzítjük őket.
- **Hiúsági számok, amiket nem tekintünk fejlődésnek:** szókincsméret, `fullnessPct`, a 3D-nézet
  csomópontjainak száma, `distilledCount`. Ezek akkor is nőnek, ha az agy nem lesz okosabb.

## 2. Programozás — a fő cél

| Mérőszám | Definíció | Készlet | Alapérték | Fázis |
|---|---|---|---|---|
| `pass@1` | a feladatok aránya, ahol az **első** megoldás minden rejtett tesztet teljesít | E2 | még nincs | P0 |
| `javítással@3` | ugyanez legfeljebb 3 javítási kör után | E2 | még nincs | P0 |
| Javítási körök | átlag a végül zöld feladatokon | E2 | még nincs | P0 |
| Idő a zöldig | medián és p90 (s), feladatonként | E2 | még nincs | P0 |
| Hibajavítás | a hibás kód + piros teszt feladatok aránya, amit zöldre javít | E4 | még nincs | P0–P3 |
| Komplex feladat | végigért, és minden részfeladat tesztje zöld | E5 | még nincs | P5 |

Cél (becslés): a P0-alapérték után 3 hónappal `javítással@3` +10 százalékpont, változatlan modellel —
így a javulás a tudástárnak és a ciklusnak tulajdonítható, nem a modellcserének.

## 3. Válaszok és nyelv

| Mérőszám | Definíció | Készlet | Alapérték |
|---|---|---|---|
| Válaszhelyesség | automatikus pontozás (kulcsszó/regex) + kézi 0–2 skála | E1 | még nincs |
| Magyar nyelvi minőség | kézi rubrika 0–2: nyelvhelyesség, természetesség, tömörség | E1 | még nincs |
| BRAIN-útválasztás | a BRAIN akkor és csak akkor válaszol, amikor tényleg lefedi a kérdést | E7 | `web/tests/brain-answers.test.ts` zöld |
| Eszközhívás | helyes eszköz + argumentumok az első körben | E3 | **mért:** `gemma4:e2b` 96,7% (LLM) / 100% (fast-path + LLM), 30 magyar parancson |

## 4. Tudás

| Mérőszám | Definíció | Cél (becslés) |
|---|---|---|
| Ellenőrzött elemek | darabszám fajtánként (`snippet`, `api-note`, `fact`, `lesson`, `error-fix`) | nő |
| Ellenőrzési arány | `verified / (verified + rejected)` forrásonként | információ: melyik forrás ér valamit |
| Tudás-precizitás | havi szúrópróba: 20 véletlen `verified` elem kézi ellenőrzése | ≥ 19/20 |
| Karantén kora | a legrégebbi karanténos elem kora | ≤ 30 nap |
| Ellentmondás, elavult | `contested` és `stale` elemek száma | csökken |
| Ismétlés sikere | `pass / esedékes` az ismétléseken | ≥ 0,85 |

## 5. Hatékonyság és erőforrás

| Mérőszám | Definíció | Alapérték |
|---|---|---|
| Agy-találati arány | `brain / (brain + web + model)` — ma is számolja a `web/src/autolearn/metrics.ts` | böngészőnként van, nem összesítve |
| Cache-találat | a cache-ből kiszolgált kérések aránya ([../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md)) | még nincs |
| Elkerült felhőhívás | felhő nélkül megoldott feladatok aránya; felhőhívás/nap | még nincs |
| Első token | medián / p90 | **mért:** `gemma4:e2b` 0,44 / 0,52 s (terheletlenül) |
| Válaszidő | kérdéstől a teljes válaszig, útvonalanként | még nincs |
| Háttér-zavarás | a felhasználó első kérésének késése önálló tanulás közben vs. terheletlenül (Δ medián, Δ p90) | még nincs |
| Megszakítási késés | felhasználói jeltől a tanulás leállásáig | még nincs (cél ≤ 1 s) |
| CPU-idő | önálló tanulás percei éjszakánként | még nincs |

Figyelem: az agy-találati arány csak azt méri, **honnan** jött a válasz, azt nem, hogy jó volt-e.
Ezért mindig a válaszhelyesség szúrópróbájával együtt értékeljük.

## 6. Biztonság — a cél mindig 0 vagy 100%

| Mérőszám | Cél |
|---|---|
| Személyes adat kijelentkezett munkamenetben (fiktív profillal próbálva) | 0 |
| Tiltott elem a tudástárban (utólagos teljes szkennelés a `canLearn`-nel) | 0 |
| Injekcióból indult művelet a próbakészleten | 0 |
| Sandbox-kitörés a kártékony próbakészleten | 0 (100% elnyelve) |
| Kapu-tiltások szabályonként | csak információ (darabszám, tartalom nélkül) |

## 7. Regressziók

- **Regresszió** = egy elem, ami az előző alapfutáson zöld volt, most piros (azonos készletverzió,
  azonos modell és beállítások).
- A biztonsági készleten (E6) **bármely** regresszió blokkoló. Máshol vizsgálandó, ha 2-nél több elem
  vagy 2 százalékpontnál nagyobb esés (becslés).
- Zajszűrés: `temperature` 0, rögzített `seed`; a piros elemeket kétszer újrafuttatjuk, hogy a
  véletlen ingadozás elváljon a valódi romlástól.

## 8. Gyűjtés — eseménynapló tartalom nélkül

```ts
type MetricEvent =
  | { t: 'answer'; ts: string; route: 'brain' | 'cache' | 'web' | 'local-model' | 'cloud'; ms: number; firstTokenMs?: number }
  | { t: 'task'; ts: string; taskId: string; set?: string; passFirst: boolean; repairs: number; green: boolean; ms: number }
  | { t: 'learn'; ts: string; source: string; outcome: 'verified' | 'hypothesis' | 'rejected' | 'blocked'; rule?: string }
  | { t: 'study'; ts: string; outcome: 'done' | 'paused' | 'failed'; pauseMs?: number; cpuS: number }
  | { t: 'eval'; ts: string; set: string; setVersion: string; model: string; score: number; items: number };
```

Szabály: az eseményben **soha nincs felhasználói szöveg** — csak azonosító, darabszám, időtartam,
szabálykód. A tárolás helye: [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md).

## 9. Mérési fegyelem

- Nehéz kiértékelés csak akkor fut, ha a felhasználó nincs a gépnél (egy Ollama-sáv; a `JARVIS_BUILD.md`
  kérése szerint mérés nem futhat a felhasználó hangos próbái alatt, mert torzítja a számokat).
- Minden futáshoz rögzítjük: modell + tag, Ollama-verzió (ma 0.40.16), készletverzió, `temperature`,
  `seed`, dátum, és hogy volt-e más terhelés.
- Csak azonos készletverzió és azonos modell eredményei vethetők össze.

## Kész, ha

- P0-ban minden E2-futás után automatikusan elkészül a `pass@1`, `javítással@3`, javítási kör és idő a zöldig;
- teszt bizonyítja, hogy a `MetricEvent`-ekben nincs felhasználói szöveg;
- a heti napló ([03-fejlodesi-naplo-sablon.md](03-fejlodesi-naplo-sablon.md)) számai ebből az eseménynaplóból jönnek;
- P6-ban a kiértékelő irányítópult ugyanezeket a mérőszámokat mutatja.

## Kapcsolódó

- [02-ertekelo-keszletek.md](02-ertekelo-keszletek.md) · [03-fejlodesi-naplo-sablon.md](03-fejlodesi-naplo-sablon.md)
- [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md) · [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
- [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
