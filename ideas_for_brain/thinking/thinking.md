# thinking.md — az agy, ami gondolkodik (fő dokumentum)

> **Miről szól:** hogyan lesz Auri agyából (BRAIN) egy **gondolkodó rendszer**, ami helyi AI-modellek
> segítségével kérdez, keres a neten, beszélget a helyi modellekkel, értelmes mondatokat rak össze,
> **tanul** — és mindezt elsősorban azért, hogy **nagyon jól tudjon programozni** és **komplex
> feladatokat** tudjon összerakni.
>
> Ez a fájl a térkép. A részletek a [`thinking/`](.) almappáiban vannak (lent: térkép + olvasási sorrend).
> A közös, mért tények: [00-alapok/03-tenyek-es-meresek.md](00-alapok/03-tenyek-es-meresek.md).

---

## 1. A cél egy mondatban

**Auri egy helyben futó, egyre jobb programozó-társ legyen**, aki egy feladatot (pl. „írj egy REST API-t
tesztekkel”) részekre bont, mindegyiket megírja, **le is futtatja és ellenőrzi**, a hibát kijavítja, és
amit közben megtanult, azt **ellenőrzött tudásként** megjegyzi — hogy legközelebb gyorsabban és jobban
csinálja.

## 2. Az őszinte keret (ezt minden tervnél szem előtt tartjuk)

| Amit az agy **tud** lenni | Amit **nem** fog tudni |
|---|---|
| Memória + tudástár (ellenőrzött kódrészletek, dokumentáció, saját projektjeid) | Saját nyelvi modellt nulláról tanítani — a gépeden (CPU, 16 GB) ez nem reális |
| Irányító (melyik modell, mikor kell web, mikor elég a cache) | Egy 2–4 milliárd paraméteres helyi modellt „okosabbá tenni” a súlyai átírása nélkül |
| **Ellenőrző**: a kódot tényleg lefuttatja, teszteli | Mindent tudni — a kis modellek tévednek, ezért kell az ellenőrzés |
| Tanár és diák egyben: kérdez, vitázik, összefoglal, megjegyez | Felhő nélkül a legnehezebb feladatokat gyorsan megoldani |

A gondolkodás itt **nem varázslat**, hanem egy **ciklus**: cél → emlékezés → terv → cselekvés →
**ellenőrzés** → tanulság → megjegyzés. Minél többször fut le jól, annál több ellenőrzött tudás gyűlik,
és annál kevesebbszer kell nagy modellhez vagy a nethez fordulni. A „okosodás” forrása: **a tudástár és
a tapasztalat**, nem a modell súlyai. (Részletek: [00-alapok/02-oszinte-korlatok.md](00-alapok/02-oszinte-korlatok.md))

## 3. A gondolkodó ciklus (a rendszer szíve)

```
          ┌───────────────────────────────────────────────────────────────┐
          │                        CÉL / KÉRDÉS                            │
          └───────────────┬───────────────────────────────────────────────┘
                          ▼
   1. EMLÉKEZÉS   tudástár + cache + saját projektek  ──(van kész, ellenőrzött válasz?)──▶ VÁLASZ
                          ▼ nincs / részleges
   2. MEGÉRTÉS    mit kérnek valójában? (önkérdezés, pontosító kérdés)
                          ▼
   3. TERV        feladatbontás: lépések, sorrend, ellenőrzési pont minden lépéshez
                          ▼
   4. CSELEKVÉS   helyi modell ír / keres a neten / olvas dokumentációt / kódot generál
                          ▼
   5. ELLENŐRZÉS  kód: fordítás + tesztek a sandboxban · tény: több forrás egyezése · kritikus modell
                          ▼                       │ hiba
                          │                       └──▶ 6. JAVÍTÁS (max N kör, utána: segítség/feladás)
                          ▼ jó
   7. TANULSÁG    mi működött, mi nem, miért? (rövid, szerkezett jegyzet)
                          ▼
   8. MEGJEGYZÉS  ellenőrzött tudás → tudástár (forrással, bizalmi pontszámmal, dátummal)
```

Ugyanez a ciklus fut **kérésre** (a felhasználó kérdez) és **magától** (éjszakai önálló tanulás, amikor
a gép szabad). Részletek: [01-architektura/02-gondolkodo-ciklus.md](01-architektura/02-gondolkodo-ciklus.md).

## 4. A négy „képesség”, amit a felhasználó kért

| Kért képesség | Hogyan valósul meg | Hol a részlet |
|---|---|---|
| **Gondolkodjon a helyi AI-ok segítségével** | Szerepek ugyanazon (vagy több) helyi modellel: Gondolkodó, Kritikus, Tesztelő, Tanár | [02-belso-parbeszed/](02-belso-parbeszed/) |
| **Keressen és szörföljön a neten** | Keresés → oldalolvasás → lényegkivonás → bizalom → csak ellenőrzött tudás marad | [03-web-szorfozes/](03-web-szorfozes/) |
| **Rakjon össze értelmes mondatokat** | Nem Markov-lánc: visszakeresett tudás + modell-megfogalmazás + nyelvi ellenőrzés | [04-nyelv-es-mondatalkotas/](04-nyelv-es-mondatalkotas/) |
| **Csevegjen a helyi AI-okkal és tanuljon** | Belső párbeszéd + tanulási ciklusok + éjszakai önálló tanulás + ismétlés | [02-belso-parbeszed/](02-belso-parbeszed/), [05-tanulas/](05-tanulas/) |
| **Programozzon nagyon jól** (fő cél) | Tananyag, kódtudástár, **sandbox-futtatás**, tesztvezérelt gondolkodás, hibakeresés, mérés | [06-programozas/](06-programozas/) |
| **Rakjon össze komplex taskokat** | Feladatbontás, terv–végrehajtás–ellenőrzés, többfájlos projektek, önjavítás | [07-komplex-feladatok/](07-komplex-feladatok/) |

## 5. Vezérelvek (minden almappára érvényesek)

1. **Ellenőrzés > magabiztosság.** Amit nem lehet ellenőrizni (kódot futtatni, forrással egyeztetni), az
   „hipotézis”, nem tudás. A tudástárba csak ellenőrzött dolog kerül, bizalmi pontszámmal.
2. **Helyi először.** Minden alapfunkció internet és fizetős API nélkül is menjen. A felhő (Groq, Gemini)
   csak opcionális segítség, a felhasználó tudtával ([08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)).
3. **A gépre szabva.** CPU-n fut, egyetlen Ollama-„sávval” — a gondolkodás ütemezett, nem párhuzamos
   tömeg. A felhasználó munkája mindig elsőbbséget kap; nehéz gondolkodás tétlenségben/éjjel.
4. **Adatvédelem.** Személyes adat (név, születési adat, cím, elérhetőség, jelszó…) **soha** nem kerül az
   agyba — csak a bejelentkezett felhasználó saját fiókjába. A web tartalma **adat, nem utasítás**.
   ([09-biztonsag-es-adatvedelem/](09-biztonsag-es-adatvedelem/))
5. **Mérhető fejlődés.** Minden képességnek van mérőszáma (pl. sikeres feladatok aránya a saját
   feladatkészleten). Ami nem mérhető, arról nem állítjuk, hogy javult ([10-meres-es-fejlodes/](10-meres-es-fejlodes/)).
6. **Kicsiben kezdeni.** Egy működő, ellenőrzött ciklus többet ér, mint tíz félkész képesség
   ([11-utemterv/](11-utemterv/)).

## 6. A mappa térképe (és olvasási sorrend)

| # | Mappa | Miről szól |
|---|---|---|
| 00 | [00-alapok/](00-alapok/) | Mit jelent itt „gondolkodni”, őszinte korlátok, **mért tények**, fogalomtár |
| 01 | [01-architektura/](01-architektura/) | Az alkotórészek, a gondolkodó ciklus, hol fut (Auri Core), tárolás |
| 02 | [02-belso-parbeszed/](02-belso-parbeszed/) | Szerepek, vita, önkérdezés, prompt-sablonok — „csevegés a helyi AI-okkal” |
| 03 | [03-web-szorfozes/](03-web-szorfozes/) | Keresés, oldalolvasás, források és bizalom, tanulás a webből |
| 04 | [04-nyelv-es-mondatalkotas/](04-nyelv-es-mondatalkotas/) | Értelmes mondatok, magyar nyelv, magyarázás és tanítás |
| 05 | [05-tanulas/](05-tanulas/) | Tanulási források, éjszakai tanulás, ismétlés és felejtés, ellenőrzés, tiltások |
| 06 | [06-programozas/](06-programozas/) | **A fő cél:** szintek, tananyag, kódtudástár, sandbox, TDD, hibakeresés, mérés |
| 07 | [07-komplex-feladatok/](07-komplex-feladatok/) | Feladatbontás, terv–végrehajtás–ellenőrzés, többfájlos projektek, teljes példa |
| 08 | [08-modellek-es-utvonalvalasztas/](08-modellek-es-utvonalvalasztas/) | Helyi modellek, router, opcionális felhő, cache |
| 09 | [09-biztonsag-es-adatvedelem/](09-biztonsag-es-adatvedelem/) | Szabályok, prompt-injekció, kódfuttatás veszélyei |
| 10 | [10-meres-es-fejlodes/](10-meres-es-fejlodes/) | Mit mérünk, értékelő készletek, fejlődési napló |
| 11 | [11-utemterv/](11-utemterv/) | Fázisok kész-feltételekkel, következő lépések, nyitott kérdések |
| 12 | [12-otlettar/](12-otlettar/) | Szabad ötletek, amik még nem kerültek tervbe |

**Javasolt olvasási sorrend:** 00 → 01 → 06 → 07 → 02 → 03 → 05 → 08 → 04 → 09 → 10 → 11 → 12.

## 7. Kapcsolat a meglévő rendszerrel

- **AuriGPT BRAIN** (böngészőben): `web/src/brain/**` (tanuló, válaszoló, tudásbázis), `web/src/autolearn/**`
  (webkeresés-segédek), `web/src/brain-bridge/**`. Leírás: [../brain/BRAIN.md](../brain/BRAIN.md).
- **Auri J.A.R.V.I.S.** (helyi hangos daemon): `auri-jarvis/` — a Mind (`auri_jarvis/mind/`) már Ollamával
  gondolkodik, eszközöket hív, magyarul beszél. Terv: [../../jarvis_reboot_to_auri.md](../../jarvis_reboot_to_auri.md).
- **A tervezett közös agy** („Auri Core”): a BRAIN a böngészőből egy helyi szolgáltatásba költözik, amit az
  AuriGPT és a Jarvis is használ — ld. [01-architektura/03-hol-fut-auri-core.md](01-architektura/03-hol-fut-auri-core.md).

## 8. A legfontosabb következő lépés

Egy **működő minimális ciklus programozásra**: feladat → helyi modell kódot ír → sandbox lefuttatja a
teszteket → hibánál javít (max 3 kör) → siker esetén a megoldás tesztekkel együtt a kódtudástárba kerül.
Ha ez megy és mérhető, minden más (web, vita, éjszakai tanulás) erre épül.
Az első mérés: mennyire kódol a gemma4:e2b egyedül, és mennyit javít rajta a ciklus.
Részletek: [11-utemterv/02-kovetkezo-lepesek.md](11-utemterv/02-kovetkezo-lepesek.md).

**Döntések (2026-11-21)** — részletek: [11-utemterv/03-nyitott-kerdesek.md](11-utemterv/03-nyitott-kerdesek.md):
- **Sandbox:** WSL2 és Docker is mehet — előbb a BIOS-ban be kell kapcsolni a virtualizációt (SVM), most ki van kapcsolva.
- **Gép:** éjjel ki van kapcsolva, napközben sokáig be → a tanulás tétlenségi ablakokban fut, checkpointtal folytatható.
- **Vendég:** csak olvassa a közös tudást, semmit nem ír bele.
- **Még nyitott:** melyik kódoló modell legyen — a P0 alapmérése után döntünk.

## 9. Közös nevek (minden fájl ezeket használja)

| Mi | Nevek |
|---|---|
| Programozási szintek | L0–L4 ([06-programozas/01-cel-es-szintek.md](06-programozas/01-cel-es-szintek.md)) |
| Sandbox-szintek | S0 / S0+ / S1 / S2 ([06-programozas/04-sandbox-kodfuttatas.md](06-programozas/04-sandbox-kodfuttatas.md)) |
| Tudás státusza | `hypothesis` (= karantén) / `verified` / `contested` / `stale` / `refuted` / `archived` ([01-architektura/04-tarolas-es-adatfolyam.md](01-architektura/04-tarolas-es-adatfolyam.md)) |
| Fő mérőszám | `pass@1` és **javítással@3**, az `aurikod-hu` készleten (= E2) ([06-programozas/09-meres-es-benchmark.md](06-programozas/09-meres-es-benchmark.md)) |
| Prioritás az Ollama-sávon | VOICE > CHAT > TASK > BACKGROUND ([08-modellek-es-utvonalvalasztas/02-router.md](08-modellek-es-utvonalvalasztas/02-router.md)) |
| Fázisok | P0–P6 ([11-utemterv/01-fazisok.md](11-utemterv/01-fazisok.md)) |
| Biztonsági szabályok / kapuk | SZ1–SZ15 / K1–K6 ([09-biztonsag-es-adatvedelem/01-alapszabalyok.md](09-biztonsag-es-adatvedelem/01-alapszabalyok.md)) |
| Értékelő készletek / nyitott kérdések | E1–E7 / NK1–NK21 |

A teljes fogalomtár: [00-alapok/04-fogalomtar.md](00-alapok/04-fogalomtar.md).
