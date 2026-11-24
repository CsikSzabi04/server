# Értelmes mondatok — visszakeresés, megfogalmazás, ellenőrzés

> **Miről szól:** mitől „értelmes” egy válaszmondat, miért nem Markov-lánccal készül, hogyan áll össze
> visszakeresett tudásból + modell-megfogalmazásból + gépi ellenőrzésből, és mit tanultunk a BRAIN
> 2026-11-20-i hibáiból (a „ki vagy?” kérdésre az emberi testről válaszolt).

## 1. Mit értünk értelmes mondaton?

Négy feltétel, mind egyszerre:

| Feltétel | Kérdés | Hogyan ellenőrizzük |
|---|---|---|
| **Nyelvileg helyes** | magyar/angol nyelvtan, helyesírás | nyelvfelismerés + helyesírás-ellenőrzés ([02-magyar-nyelv.md](02-magyar-nyelv.md)) |
| **Arról szól, amit kérdeztek** | a kérdés típusa és tárgya egyezik | szándék-felismerés, nem kulcsszó-előfordulás |
| **Igaz (megalapozott)** | minden állítás mögött forrás vagy ellenőrzés áll | forrás-azonosító állításonként |
| **Illik a helyzethez** | nyelv, hossz, mód (hang / szöveg / kód) | szabályok a kimeneten |

## 2. Miért nem Markov-lánc?

A Markov-lánc a következő szót az előző egy-két szó alapján sorsolja. Rövid távon „magyarosan
hangzik”, de **nincs benne jelentés, cél és igazság**: nem tudja, mit kérdeztek, és nem tudja, igaz-e,
amit mond. Kis korpuszon ráadásul halandzsázik — a mai `web/src/brain/answer.ts` ezért már csak
utolsó mentsvárként említi, és szándékosan **nem** ad vissza nyers Markov-szöveget.

| Módszer | Gyors? | Folyékony? | Igaz? | Mire jó |
|---|---|---|---|---|
| Markov-lánc | igen | rövid távon | **nem** | semmire a válaszban; legfeljebb szókincs-statisztika |
| Sablon (`"Tessék, egy működő példa — {cím}"`) | igen | igen | ha a kitöltés igaz | rövid, fix mondatok, rendszerüzenetek |
| Ellenőrzött kártya mondata szó szerint | igen | igen | igen | definíció, tény, ha pontosan erre kérdeztek |
| Modell-megfogalmazás **terv + források alapján** | lassabb | igen | ha a terv igaz és ellenőrizzük | minden, ami több darab tudás összefűzése |

A BRAIN szerepe tehát: **memória + irányító + ellenőrző** — a mondatot a modell fogalmazza, de *azt*
mondja ki, amit a BRAIN odaadott, és a BRAIN ellenőrzi, mielőtt kimegy.

## 3. A 2026-11-20-i hibák tanulságai

Két valódi képernyőkép (javítva 2026-11-21-én, regressziós tesztek: `web/tests/brain-answers.test.ts`,
`auri-jarvis/tests/mind/test_mind_fastpath.py`):

| Kérdés | A BRAIN válasza | Ok |
|---|---|---|
| „ki vagy?” | az emberi testről (angolul) | a „v**agy**” részszövegként tartalmazza az „agy” kulcsszót |
| „de a brain miért nem tud jól válaszolni?” | az időjárásról | a „b**rain**” tartalmazza a „rain”-t |
| „hogy vagy?” | az emberi testről | ugyanaz a „vagy” ⊃ „agy” |
| „írj egy python függvényt…” | a Python definíciója | egy **feladatra** definícióval felelt |
| „nem” / „nmem” | a felhasználó teljes személyes profilja — kijelentkezve is | személyes adat került az agyba |

**Tanulságok — ezek szabályok a gondolkodó agyban is:**
1. **Illesztés szóhatáron vagy jelentés alapján**, soha nem puszta részszövegre. A javítás
   (`keywordScore` a `seed/knowledge.ts`-ben): a kulcsszónak szót kell **kezdenie**, rövid tőhöz
   legfeljebb 3 betűs toldalék járhat, a rövid szóra végződő kifejezés pontosan végződik.
2. **„Előfordul a kulcsszó” ≠ „erről kérdeznek”.** Kell a kérdés **típusa** is: definíciót kérnek
   (`ASKS_ABOUT`), vagy feladatot / összehasonlítást / hibakeresést / valós idejű adatot
   (`NEEDS_MODEL`) — az utóbbira kész definíció rossz válasz.
3. **Bizonytalan → hallgass, és add tovább** (tudástár → web → modell). Egy rossz „gyors” válasz
   többet árt, mint egy lassabb jó.
4. **Minden valódi hiba regressziós teszt lesz** — a „ki vagy?” azóta mindkét kódbázis tesztje.
5. **Személyes adat soha nem kerül az agyba** — csak a bejelentkezett felhasználó fiókjába.

## 4. A mondatalkotás csővezetéke

```
kérdés ─▶ 1. SZÁNDÉK      definíció | hogyan | feladat | hibakeresés | összehasonlítás | csevegés | valós idejű
       ─▶ 2. VISSZAKERESÉS tudáskártyák (forrás-azonosítóval), kód-snippetek, (web, ha kell)
       ─▶ 3. TARTALOMTERV  pontok listája, mindegyikhez forrás-id vagy "bizonytalan"   ← BRAIN, nem modell
       ─▶ 4. MEGFOGALMAZÁS a modell a terv alapján fogalmaz (T8 sablon)
       ─▶ 5. ELLENŐRZÉS    gépi szabályok (5. pont) ── bukik ──▶ 1× újrafogalmazás, utána a terv szó szerint
       ─▶ kimenet
```

Ha a terv egyetlen ellenőrzött kártya, és a kérdés pontosan arra vonatkozik, a 4. lépés **kimarad**: a
kártya mondata megy ki (így működik ma a `findKnowledge` is) — modell nélkül, ezredmásodpercek alatt.

```json
{ "lang": "hu", "mode": "text", "intent": "how_to",
  "points": [
    { "text": "Python 3.9-től: str.removeprefix(prefix)", "src": "k12", "state": "ellenőrzött" },
    { "text": "Régebbi verzión: s[len(p):] if s.startswith(p) else s", "src": "k13", "state": "ellenőrzött" },
    { "text": "A bytes típuson is van ilyen metódus", "src": null, "state": "bizonytalan" }
  ],
  "code": { "lang": "python", "ref": "k12" } }
```

## 5. Ellenőrzések (gépi, olcsók)

| Ellenőrzés | Szabály | Ha bukik |
|---|---|---|
| Nyelv | a válasz nyelve = a kérdés nyelve (közös `detectLang`) | újrafogalmazás |
| Forráslefedés | minden tényállítás-mondatban `[k…]` hivatkozás, vagy „bizonytalan” jelölés | újrafogalmazás |
| Számok, verziók, nevek | minden szám / verzió / API-név szerepel a tervben vagy a forrásban | a mondat törlése |
| Kód | a kódblokk a tervben hivatkozott, **lefuttatott** kód; ha nem futott, „nem futtattam” | jelölés |
| Hallucináció-őr | nincs múlt idejű „megcsináltam/megnyitottam” sikeres eszközhívás nélkül (a Jarvis Mind szabálya) | a mondat törlése |
| Hossz / mód | hangmód: 1–3 rövid mondat, markdown nélkül (Jarvis persona); szöveg: a szándékhoz illő | rövidítés |
| Személyes adat | `isPersonal` mintájú szűrés | a rész kitakarása |

Mind determinisztikus kód, a válaszidőhöz alig ad hozzá (becslés: ezredmásodpercek). Modell csak az
egyszeri újrafogalmazáshoz kell; ha az is bukik, a tartalomterv pontjai mennek ki felsorolásként —
csúnyább, de igaz.

## 6. Kész, ha

1. A regressziós készlet (a 3. pont kérdései + a `brain-answers.test.ts` esetei) az új csővezetéken is zöld.
2. Egy 50 kérdéses vegyes készleten (definíció, hogyan, feladat, hibakeresés) a válaszok ≥ 95%-a a
   megfelelő **szándékú** úton megy (célérték, mérni kell), és nulla válaszban van forrás nélküli szám
   vagy verzió.
3. A forrás nélküli állítások aránya mérve van, és nem nő a modellcsere után sem
   ([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

## Kapcsolódó

- [02-magyar-nyelv.md](02-magyar-nyelv.md) · [03-magyarazas-es-tanitas.md](03-magyarazas-es-tanitas.md)
- [../02-belso-parbeszed/04-prompt-sablonok.md](../02-belso-parbeszed/04-prompt-sablonok.md) (T8 Fogalmazó)
- [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) — honnan jön az „ellenőrzött”
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — melyik út felel
- [../00-alapok/02-oszinte-korlatok.md](../00-alapok/02-oszinte-korlatok.md) · [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md)
