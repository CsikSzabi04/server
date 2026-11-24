# Cél és szintek — a programozó-létra

> **Miről szól:** mit jelent **mérhetően**, hogy Auri „nagyon jól programoz”; az öt szint (L0 szintaxis →
> L4 komplex, többfájlos feladat) szintenkénti kész-feltételekkel; és mely nyelvekkel kezdünk. Minden szám
> itt **célérték** (nem mért) — a mért tények: [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md).

## 1. Mit jelent itt „jól programozni”

Nem érzés, hanem hét ellenőrizhető tulajdonság. Ami nem mérhető, arról nem mondjuk, hogy javult.

| Tulajdonság | Mit jelent nálunk | Hogyan mérjük |
|---|---|---|
| **Helyes** | a megoldás a *rejtett* teszteken is átmegy, nem csak a látottakon | rejtett tesztek aránya ([09](09-meres-es-benchmark.md)) |
| **Ellenőrzött** | Auri soha nem mond „kész”-t futtatás nélkül (a Jarvis hallucináció-őrének kódos párja) | minden „kész” mögött van `RunResult` ([04](04-sandbox-kodfuttatas.md)); a hamis „kész” száma = 0 |
| **Idiomatikus** | `tsc --strict` és `ruff` tiszta, követi a projekt konvencióit | lint-/típushibák száma megoldásonként |
| **Önjavító** | a hibaüzenetből javít, nem találgat | javítási körök átlaga, „nincs előrelépés” arány ([05](05-tesztvezerelt-gondolkodas.md)) |
| **Újrahasznosító** | ellenőrzött tudásból dolgozik, nem mindig nulláról | tudástár-találati arány ([03](03-kod-tudasbazis.md)) |
| **Őszinte** | ha a keret elfogy, megmondja, hol akadt el, és mi hiányzik | feladási jelentés a költségvetés végén |
| **Magyaráz** | magyarul, röviden elmondja, mit és miért csinált | kézi pontozás 1–5, mintavétellel |

## 2. A létra

| Szint | Név | Mit tud | Példafeladat | Ellenőrzés | Fázis |
|---|---|---|---|---|---|
| **L0** | Szintaxis és idiómák | rövid kifejezések, nyelvi alapelemek helyesen | „szűrd ki a páros számokat” | 1–3 teszt | P0 |
| **L1** | Egyetlen függvény | adott szignatúrájú tiszta függvény, a széleseteket is kezeli | `slugifyHu(s)`, `parse_forint(s)` ([08](08-gyakorlofeladatok.md)) | 5–15 teszt + rejtett + tulajdonságteszt | P0 |
| **L2** | Modul | több függvény/osztály egy fájlban, állapot, hibakezelés, async, injektált függőség (óra, I/O) | rate limiter, LRU-cache, CSV-összesítő | modulteszt + típusellenőrzés + lint | P1–P3 |
| **L3** | Kis projekt | 2–6 fájl: CLI vagy REST-végpont, SQLite, tesztek, rövid README | Express todo API memóriatárral + tesztek | projekt-tesztcsomag (S1 sandbox) | P5 eleje |
| **L4** | Komplex, többfájlos feladat | feladatbontás, terv, lépésenkénti ellenőrzés, **meglévő** kódbázis módosítása | „adj bejelentkezést a meglévő API-hoz, tesztekkel” | lépésenkénti + végső tesztcsomag + regresszió | P5–P6 |

Az L3–L4 menetét a [../07-komplex-feladatok/](../07-komplex-feladatok/01-feladatbontas.md) írja le; ez a mappa a
„téglákat” (L0–L2) és a közös gépezetet (sandbox, TDD, tudástár, mérés) adja hozzá.

## 3. Szintenkénti kész-feltételek (célértékek, nem mért)

A mérés mindig az adott szint **rejtett (held-out) készletén** történik ([09](09-meres-es-benchmark.md)), legalább
60 feladaton nyelvenként (kevesebb feladatnál a bizonytalanság túl nagy). Jelölés: **pass@1** = első próbálkozás
javítás nélkül; **javítással@3** = legfeljebb 3 javítási kör után.

- **L0 kész, ha** javítással@3 ≥ 90 %, és a naplókban nincs egyetlen futtatás nélküli „kész” állítás sem.
- **L1 kész, ha** javítással@3 ≥ 75 %, pass@1 ≥ 50 %, a sikeres megoldások ≥ 90 %-a lint- és típustiszta, és a
  feladatonkénti medián falióra ≤ 8 perc (a 7. pont becsléséből).
- **L2 kész, ha** javítással@3 ≥ 60 %, típushiba nélkül; az injektált órát/fájlrendszert helyesen kezeli (nincs
  valódi várakozás, nincs írás a futási mappán kívül); a regressziós készlet zöld.
- **L3 kész, ha** a kis projektek ≥ 50 %-a teljesen zöld tesztcsomaggal készül el; a többinél a terv lépéseinek
  ≥ 70 %-a zöld, és Auri pontosan megnevezi a hiányzó részt.
- **L4 kész, ha** ≥ 40 % teljes siker, és **minden** sikeresnek mondott esetben a meglévő kódbázis korábbi tesztjei
  is zöldek maradnak (0 regresszió).

## 4. Mi kell az agyból az egyes szintekhez

● = kötelező, ○ = hasznos, – = nem kell.

| Komponens | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| Sandbox S0 (korlátozott alfolyamat) — [04](04-sandbox-kodfuttatas.md) | ● | ● | ● | – | – |
| Sandbox S1 (WSL2/konténer) | – | – | ○ | ● | ● |
| Tesztvezérelt ciklus — [05](05-tesztvezerelt-gondolkodas.md) | ○ | ● | ● | ● | ● |
| Kódtudástár — [03](03-kod-tudasbazis.md) | ○ | ● | ● | ● | ● |
| Hibakeresés + hibaüzenet-tudástár — [06](06-hibakereses.md) | ○ | ● | ● | ● | ● |
| Belső párbeszéd (Kritikus, Tesztelő) — [../02-belso-parbeszed/01-szerepek.md](../02-belso-parbeszed/01-szerepek.md) | – | ○ | ● | ● | ● |
| Webes kutatás (API-kérdések) — [../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md) | – | ○ | ○ | ● | ● |
| Saját projektek ismerete — [07](07-sajat-projektekbol-tanulas.md) | – | – | ○ | ○ | ● |
| Feladatbontás — [../07-komplex-feladatok/01-feladatbontas.md](../07-komplex-feladatok/01-feladatbontas.md) | – | – | ○ | ● | ● |

## 5. Nyelvi sorrend

Szabály: egy nyelv csak akkor „tanítható”, ha a sandbox le tudja futtatni a tesztjeit. Amíg nem, addig csak
tudáskártya lehet belőle (legfeljebb T1 bizalom, ld. [03](03-kod-tudasbazis.md)).

| Sorrend | Nyelv | Miért | Futtatható ma? (ellenőrizve 2026-11-21) |
|---|---|---|---|
| 1 | **TypeScript / JavaScript (Node)** | a felhasználó fő stackje (`web/`, `server/`) | igen — Node v24.14.0, TypeScript 5.9.3 (`web/node_modules`) |
| 1 | **Python** | a Jarvis nyelve, gyors pytest-ciklus | igen — Python 3.12.6 |
| 2 | **SQL (SQLite-dialektus)** | adatbázis-feladatok szerver nélkül | igen — a Python beépített `sqlite3`-ja |
| 3 | React (TSX) | a `web/` felülete | később: DOM-emuláció (pl. jsdom) kell a sandbox-futtatókörnyezetbe |
| 4 | PostgreSQL (Supabase), MySQL, Oracle | a tudásbázis lefedi, dialektuseltérések | csak tudáskártya, amíg nincs DB-konténer (S1) |
| 5 | Java, Kotlin, PHP | a tudásbázisban szerepelnek | JDK/PHP nincs ellenőrizve → csak L0-tudás |
| – | HTML/CSS/Tailwind | a `recipes.ts` zöme | csak statikus ellenőrzés (parse) → bizalmi plafon T1 |

## 6. Szintlépés és visszaesés

```ts
type Level = 0 | 1 | 2 | 3 | 4;
interface LevelStatus {
  lang: 'ts' | 'py' | 'sql';
  model: string;          // a szint a MODELL + AGY párosra vonatkozik (pl. 'gemma4:e2b')
  level: Level;           // igazolt szint (csak hivatalos held-out mérés léptet)
  practicing: Level;      // amit éppen gyakorol (08)
  heldoutRepair3: number; // javítással@3 az utolsó hivatalos mérésen (0..1)
  n: number;              // feladatszám a mérésben
  evalRunId: string;      // hivatkozás a 09-es futásra
  suspect: boolean;       // regresszió gyanúja → nincs szintlépés, amíg ki nem javul
}
```

- **Szintlépés:** csak a heti held-out mérés eredménye léptet; a gyakorlás sikere nem (ott tanult is a feladatokból).
- **Visszaesés:** ha a regressziós készlet páros összevetésben szignifikánsan romlik ([09](09-meres-es-benchmark.md)
  7. pont), a státusz `suspect`, és a hiba okát a fejlődési naplóba kell írni ([../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md](../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md)).
- **Modellcsere** (pl. kódmodell telepítése): minden szint újramérése, a régi eredmény archív marad.
- **Gyakorlási arány:** 70 % aktuális szint, 20 % következő szint, 10 % hibakeresési feladat ([08](08-gyakorlofeladatok.md)).

## 7. Időkeret — őszintén

A gemma4:e2b mért generálási sebessége ~6,2 token/s. Egy L1-megoldás 150–400 token, vagyis generálásonként
~25–65 s (**számolt becslés**); tesztírással és 3 javítási körrel ez több perc. Egy 7B-s kódmodell CPU-n ennél
lassabb lehet (**mérni kell**). Következmény:

| Szint | Hogyan fut | Mit lát a felhasználó |
|---|---|---|
| L0–L1 | kérésre, interaktívan | „dolgozom rajta” + rövid állapot körönként |
| L2 | kérésre, de hosszabb | lépésenkénti állapot, megszakítható |
| L3–L4 | háttérben / éjjel, tétlenségben | haladási jelentés, a végén összefoglaló + tesztkimenet |

Fontos: a gemma4:e2b **nem kódmodell**; a kódolási képességét a gépen még nem mértük. A P0 első feladata ezért
egy **alapmérés** (modell egyedül vs. modell + agy) — ld. [09](09-meres-es-benchmark.md) 6. pont.

## 8. Amit szándékosan nem célzunk (most)

- versenyprogramozás és egzotikus algoritmusok elsőként — a hétköznapi fejlesztői feladatok előbbre valók;
- nagy kódbázis egyben átírása — L4 is kis, ellenőrzött lépésekben dolgozik;
- böngészős UI-tesztek, natív mobil- és Java-build — amíg a sandbox nem tudja futtatni;
- „gyors, magabiztos” válasz ellenőrzés nélkül — ez a vezérelvekkel ([../thinking.md](../thinking.md) 5. pont) ellentétes.

## Kapcsolódó

- [02-tananyag.md](02-tananyag.md) · [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [09-meres-es-benchmark.md](09-meres-es-benchmark.md)
- [../00-alapok/02-oszinte-korlatok.md](../00-alapok/02-oszinte-korlatok.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
- [../07-komplex-feladatok/01-feladatbontas.md](../07-komplex-feladatok/01-feladatbontas.md) · [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md)
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md)
