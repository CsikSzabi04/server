# Őszinte korlátok

> **Miről szól:** mit tudnak és mit nem a kis, CPU-n futó helyi modellek ezen a gépen; miért az
> **ellenőrzés + memória** az egyetlen járható út az „okosodáshoz”; és milyen hibamódokra kell
> számítani (mindegyikhez védekezéssel és hivatkozással).

## 1. A keret számokban (csak a mért adatok)

Forrás: [03-tenyek-es-meresek.md](03-tenyek-es-meresek.md). Ami ebből levezetett, az jelölve.

| Mért tény | Mit jelent a gondolkodásra |
|---|---|
| Ryzen 5 5500, 16 GB RAM, **csak CPU** | egyszerre egy kis/közepes modell; 9B+ csak óvatosan |
| **Egy Ollama-sáv** (`OLLAMA_NUM_PARALLEL=1`) | nincs párhuzamos „vita”: a szerepek egymás után beszélnek |
| gemma4:e2b ~6,2 tok/s, e4b ~3,0 tok/s | 1000 token kimenet ≈ 2,7 perc (e2b) / ≈ 5,6 perc (e4b) — *levezetés* |
| 1. token 0,44 s (e2b, meleg előtag) | rövid válasz gyorsan jön, **ha** az előtag a cache-ben van |
| prefixváltás ~6 s (e2b) / ~17 s (e4b) | minden rendszerprompt-csere drága → egy közös szerepkönyv, csak hozzáfűzés |
| hideg betöltés 18,5 s (e2b) – 38,3 s (qwen3.5:4b) | modellcsere fél perc is lehet → kevés modell, kötegelt munka |
| eszközhívás 96,7% (LLM) / 100% (fast-path + LLM), 30 magyar parancson | szűk, jól leírt feladatban a kis modell is megbízható |
| magyar tény-hiba: „Ausztrália fővárosa: Sydney” | tényt **nem** fogadunk el ellenőrzés nélkül |
| kódolómodell **nincs telepítve** | a programozás eleinte általános kis modellel indul |

## 2. Mit tudnak a kis helyi modellek? (becslés, a P0-ban mérni kell)

| Feladat | Várható megbízhatóság | Mit kezdünk vele |
|---|---|---|
| Rövid átfogalmazás, összefoglalás ismert szövegből | jó | a tudástárból vett tény modell-megfogalmazással |
| Osztályozás, kulcsszó, szándék felismerése | jó, ha a kimenet JSON-sémához kötött | strukturált kimenet (`format` JSON-séma) |
| Eszközhívás szűk eszközkészlettel | jó (mért, ld. fent) | átvesszük a Jarvis agent-körét |
| Egy rövid, egyfájlos függvény tesztekkel | közepes — gyakran 1–3 javítással | **P0 erre épül**: sandbox + max 3 javítási kör |
| Tények (főleg magyarul) | gyenge | csak forrással vagy tudástárból; különben „nem tudom biztosan” |
| Friss könyvtár-API-k | gyenge (tanítási adat elavul) | hivatalos dokumentáció a webről, verziócímkével |
| Hosszú, többfájlos kód egy menetben | rossz | feladatbontás, fájlonkénti ellenőrzés (P5) |
| Saját kimenet kritikája | gyenge — ugyanaz a modell ugyanott vak | külső ellenőrzés előbb; Kritikus csak kiegészítés (P3) |
| Számolás, pontos logika fejben | gyenge | eszközzel / kóddal számoltatjuk |

## 3. Miért az ellenőrzés + memória az út?

A súlyokat nem tanítjuk (CPU-n, 16 GB-on ez nem reális), tehát a modell ugyanolyan „okos” marad. Ami
változhat:

1. **Külső igazságjel:** a teszt zöld vagy piros, a fordító elfogadja vagy nem, két független forrás
   egyezik vagy nem. Ez a jel **akkor is megbízható, ha a modell nem az** — ezért erre építünk.
2. **Ellenőrzött memória:** egy drága, egyszer sikerült megoldás olcsón újrahasznosítható.
3. **Jobb útvonalválasztás:** a tapasztalatból kiderül, melyik feladattípushoz melyik modell, mekkora
   keret és milyen prompt vált be.

Szemléltetés (nem mérés): ha egy feladat ciklusa átlagosan `c_ciklus` másodperc, a cache-találaté
`c_cache`, a találati arány `p`, akkor a várható költség `p·c_cache + (1−p)·c_ciklus`. Ahogy nő az
ellenőrzött tudás, nő a `p`, és a nehéz, lassú utat egyre ritkábban kell bejárni. Az „okosodás” itt
**mérhetően** azt jelenti: nő a sikerarány és a `p`, csökken a feladatonkénti LLM-idő
([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

## 4. Hibamódok és védekezés

| Hibamód | Hogyan néz ki | Védekezés | Részletek |
|---|---|---|---|
| Kitalált API / függvény | magabiztos kód nem létező metódussal | futtatás + import-ellenőrzés; hivatalos doksi a webről | [../06-programozas/06-hibakereses.md](../06-programozas/06-hibakereses.md) |
| Tesztcsalás | a modell a tesztet „javítja”, nem a kódot, vagy triviális tesztet ír | a teszt a javítás alatt **zárolt**; minimum esetszám és szélsőérték-eset | [../06-programozas/05-tesztvezerelt-gondolkodas.md](../06-programozas/05-tesztvezerelt-gondolkodas.md) |
| Javítási körforgás | A→B→A hibaváltakozás | ugyanaz a hiba-aláírás kétszer → megállás vagy eszkaláció | [../01-architektura/02-gondolkodo-ciklus.md](../01-architektura/02-gondolkodo-ciklus.md) |
| Önmegerősítő tanulás | a modell saját, ellenőrizetlen válasza „tudássá” válik | modell-kimenet = hipotézis; csak ellenőrzés léptet elő | 5. pont |
| Tudásmérgezés a webről | rossz vagy rosszindulatú oldal tartalma a tudástárba kerül | domain-bizalom, több forrás egyezése, karantén | [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) |
| Prompt-injekció | egy oldal „utasítja” a modellt | a web tartalma adat, külön jelölt blokkban; eszköz nem indítható belőle | [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md) |
| Elavult tudás | régi könyvtárverzióhoz tartozó megoldás | verziócímke, TTL, újrafuttatott tesztek | [../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md) |
| Rossz cache-találat | hasonló, de más kérdésre ad választ | csak ellenőrzött elemre; magas küszöb; mintavételes audit | ugyanott |
| Erőforrás-versengés | a háttérgondolkodás lassítja a felhasználót | egy ütemező, elsőbbség, megszakítás, csak tétlenségben | [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) |
| Gyenge magyar mondatok | nyelvtanilag sután vagy tévesen fogalmaz | sablon + nyelvi ellenőrzés; tény a tudástárból | [../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md](../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md) |
| Zajos, duplikált memória | ugyanaz tízféleképp, ellentmondások | konszolidáció, összevonás, cáfolt jelölés | [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md) |
| Mérés-csalás | a gyakorlófeladatok megoldását „bemagolja” | elkülönített, soha nem tanított értékelő készlet | [../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md) |
| Személyes adat szivárgása | tanulás közben név, cím stb. kerül a tudástárba | `isPersonal` / `is_secret` kapu minden írás előtt | [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) |

## 5. Az önmegerősítő tanulás csapdája (ma is jelen van)

A mai `web/src/brain/distill.ts` minden modellválaszt Q→A párként eltárol, a `selfStudy.ts` pedig a
modell magyarázatait tölti az agyba. Ha a modell téved, az agy a tévedést tanulja meg, és később
„saját tudásként” mondja vissza. Szabály az Auri Core-ban:

- **modell-kimenet → `hypothesis`** státusz, alacsony bizalom, látható jelöléssel;
- előléptetés `verified`-re csak: zöld teszt, ≥ 2 független megbízható forrás, vagy a felhasználó
  kifejezett megerősítése;
- a hipotézis soha nem a gyors út válasza, legfeljebb a lassú út kiindulópontja.

## 6. Reális elvárások fázisonként (becslés — mérni kell)

| Fázis | Amit reálisan várunk | Amit még **nem** |
|---|---|---|
| P0 | egyfájlos, tesztelhető függvények; a siker egy része csak javítással jön | többfájlos kód, ismeretlen könyvtárak |
| P1–P2 | a válaszok forrással; ismételt kérdés cache-ből | friss tények forrás nélkül |
| P3–P4 | kevesebb javítási kör a tanulságok miatt; éjszakai gyakorlás | emberi szintű tervezés |
| P5 | kis többfájlos projekt órák alatt, háttérben | nagy, ismeretlen kódbázis átírása |
| P6 | nehéz eset felhős segítséggel (opcionális) | felhő nélküli „mindent tud” |

## 7. Mikor mondja Auri, hogy „nem tudom”?

- nincs ellenőrzött tudás, a keret elfogyott, és a lassú út sem hozott ellenőrzött eredményt;
- a téma gyorsan változik, és nincs friss forrás (offline);
- a feladat a sandbox szabályait sértené (hálózat, projektfájlok, ismeretlen bináris).

Ilyenkor a válasz: mit próbált, mi bukott el, mi kellene a folytatáshoz (web, nagyobb modell, felhő,
pontosítás) — **őszintén, nem kitalálva**.

## Kapcsolódó

- [01-mit-jelent-gondolkodni.md](01-mit-jelent-gondolkodni.md) — a gondolkodás definíciója
- [03-tenyek-es-meresek.md](03-tenyek-es-meresek.md) — a mért számok forrása
- [../01-architektura/01-attekintes.md](../01-architektura/01-attekintes.md) — memória + irányító + ellenőrző
- [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md) — hogyan lesz a hipotézisből tudás
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) — a külső igazságjel forrása
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) — modellek és RAM
- [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) — P0–P6
