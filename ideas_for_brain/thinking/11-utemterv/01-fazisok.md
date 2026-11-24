# Fázisok (P0–P6) — a részletes ütemterv

> **Miről szól:** a gondolkodó agy hét fázisa sorrendben: cél, hatókör, szállítandók, „Kész, ha”
> feltételek, függőségek, kockázatok és durva ráfordítás. A fázisnevek a közös ütemtervből jönnek —
> minden más dokumentum ezekre hivatkozik. **Minden ráfordítás becslés.**

## 1. Áttekintés

| Fázis | Cél egy mondatban | Fő szállítandó | Előfeltétel | Ráfordítás (becslés) |
|---|---|---|---|---|
| **P0** | Minimális programozási ciklus (L0–L1) | feladat → kód → sandbox-teszt → ≤ 3 javítás → ellenőrzött megoldás tárolva | — | 5–8 nap |
| **P1** | „Auri Core” helyi szolgáltatás | az agy kiköltözik a böngészőből; SQLite; API az AuriGPT-nek és a Jarvisnak | P0 | 6–10 nap |
| **P2** | Webes kutató ciklus | keresés → olvasás → bizalom → ellenőrzés → tárolás | P1 | 4–7 nap |
| **P3** | Belső párbeszéd szerepekkel | Gondolkodó / Kritikus / Tesztelő / Tanár, mérve | P1 | 3–5 nap |
| **P4** | Éjszakai önálló tanulás | tananyag + gyakorlás + ismétlés tétlenségben | P1 (+ P2, P3 hasznos) | 4–6 nap |
| **P5** | Komplex feladatok | feladatbontás, többfájlos projektek, önjavítás | P1 (+ P3 Kritikus) | 6–10 nap |
| **P6** | Opcionális felhő-router + kódoló modell + értékelő műszerfal | útvonalválasztás mért adatok alapján | P1 + az eddigi mérések | 4–6 nap |

„Nap” = egy esti fejlesztési munkamenet AI-kódoló ügynökkel, plusz a felhasználó jóváhagyásai.

```
P0 ─▶ P1 ─┬─▶ P2 ─┐
          ├─▶ P3 ─┼─▶ P4
          │       └─▶ P5 ─▶ P6
          └─────────────────▲   (a P6 routere csak a P1-re és a mérésekre épül)
```

**Fázis-kapu szabály:** egy fázis csak akkor kész, ha a „Kész, ha” pontjai **mérve** bekerültek a
fejlődési naplóba, és a meglévő rendszer (Jarvis, AuriGPT) közben végig működött.

## 2. P0 — minimális programozási ciklus

- **Cél:** a gondolkodó ciklus egyetlen, mérhető példánya: feladat → helyi modell kódot ír → sandbox
  lefuttatja a teszteket → hibánál javít (≤ 3 kör) → siker esetén a megoldás a tesztjeivel tárolva.
- **Benne:** L0–L1 (egy függvény), TS/JS (Node) + Python; az `aurikod-hu v1` készlet (`dev` 40 + `heldout`
  60 feladat/nyelv — a 10-es mappában ez az **E2**); S0 sandbox; Ollama-kliens; hibakivonat; `VerifiedSnippet`
  / `ErrorPattern` tár (SQLite); JSONL-napló; a hiányzó LLM-mérések ([NK14](03-nyitott-kerdesek.md)).
- **Nincs benne:** web, szerepek, többfájlos projekt (L3–L4), felület, felhő, idegen kód.
- **Szállítandók:** parancssori futtató (`run`, `bench --mode model-only|+repair`), S0 a szökési próbáival,
  feladatkészlet, első fejlődésinapló-bejegyzés. Lépésenként: [02-kovetkezo-lepesek.md](02-kovetkezo-lepesek.md).
- **Kész, ha:** (1) egy feladat végigfut parancsból; (2) **első lépésként** az alapvonal mérve: gemma4:e2b
  egyedül (`model-only`), utána `+repair` — pass@1 és javítással@3; a kódoló jelöltek ugyanígy ([NK3](03-nyitott-kerdesek.md));
  (3) a szökési próbák zöldek; (4) ugyanaz a feladat másodszor a tárból jön, 0 LLM-hívással; (5) a hamis
  „kész” számláló 0; a mérés részletes feltételei: [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md) 10. pont.
- **Kockázat → enyhítés:** a kis modellek gyengén kódolnak → épp ezt mérjük, ez a kiindulópont; az S0 nem
  biztonsági határ ártó kód ellen → csak Auri saját kódja, saját feladatokon ([NK2](03-nyitott-kerdesek.md)).

## 3. P1 — „Auri Core” helyi szolgáltatás

- **Cél:** az agy kiköltözik a böngészőből egy helyi szolgáltatásba, amit az AuriGPT web és a Jarvis is használ.
- **Benne:** külön folyamat, csak `127.0.0.1`, tokennel; SQLite (`KnowledgeItem`-ek, megoldások, receptek,
  hibaminták, futások); a böngészős BRAIN **nem személyes** tudásának átvétele (`seed/knowledge.ts`,
  `programmingCurated.ts`; a `programming.ingested.ts`-ből csak licenccel — [NK16](03-nyitott-kerdesek.md));
  Ollama-ütemező elsőbbségi osztályokkal (`VOICE` > `CHAT` > `TASK` > `BACKGROUND`; amíg az NK14 (f) nincs
  mérve, `VOICE` alatt a Core semmit nem indít); tétlenség-figyelő; a P0 futtató API mögé; események a
  HUD-nak (`think.*`); **egy** közös nyelvfelismerő ([NK11](03-nyitott-kerdesek.md)); a lepárolt modellválaszok csak
  karanténban ([NK12](03-nyitott-kerdesek.md)); vendégnek csak olvasás ([NK17](03-nyitott-kerdesek.md)); az S1 sandbox (WSL2, ha jóváhagyod — [NK2](03-nyitott-kerdesek.md)).
- **Nincs benne:** új képesség — csak átköltözés és egységesítés.
- **Szállítandók:** API (`/ask`, `/tasks` + állapot/szünet/megszakítás, `/knowledge/search`, eseményfolyam);
  AuriGPT: brain-first út a Core-on át, visszaesés a böngészős agyra; Jarvis: eszköz a Core hívására.
  Hely és technológia: [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md).
- **Kész, ha:** mindkét kliens ugyanazt a tudást látja; a Core leállásakor mindkettő hibátlanul visszaesik;
  a `JARVIS_BUILD.md` 7. szakaszához hasonló biztonsági tesztek zöldek (idegen Origin → 403, token nélkül
  → 401); fiktív személyes adatot („Teszt Elek, 1990.01.01”) az adatvédelmi szűrő (`privacy.ts`
  `isPersonal` megfelelője) elutasít; a P0 készlete a Core API-n át ugyanazt az eredményt adja.
- **Kockázat → enyhítés:** kettőzött logika TS ↔ Python → a böngészőben csak megjelenítés marad;
  porthasználat (a Jarvis HUD `:8790`, a javasolt Core `:8791`) → konfigurálható port; a hosztolt AuriGPT
  csak egy `server/`-beli proxyn érné el → eleinte csak helyi elérés, kézi indítás ([NK21](03-nyitott-kerdesek.md)).

## 4. P2 — webes kutató ciklus bizalmi pontszámmal

- **Cél:** ha a tudás hiányzik, Auri keres, olvas, kivonatol, pontoz és **ellenőriz**, mielőtt megjegyzi.
- **Benne:** kulcs nélküli keresés (a `web/api/search.ts` mintája), oldalolvasó (csak szöveg, méretkorlát),
  az `autolearn/**` segédek (újrarangsorolás, bizalom, deduplikálás, cache, rate limit, PII-szűrés)
  átvétele; forrás-rangsor (hivatalos dokumentáció > referencia > Q&A > blog); a webes kód csak
  sandbox-futtatás után kerül a tárba; a webes tartalom adat, nem utasítás.
- **Kész, ha:** 20 programozási kérdésen forrással válaszol; tényállítás csak ≥ 2 független forrással vagy
  futtatással kerül tárba; 5 prompt-injekciós tesztoldal nem változtat a viselkedésen; ismételt kérdés cache-ből jön.
- **Kockázat → enyhítés:** a keresőoldal változik / tilt → cserélhető kereső-adapter; licenc → csak
  engedélyezett licencű kód, forrással; CC BY-SA (Stack Overflow) → saját, ellenőrzött átírat + URL
  ([NK13](03-nyitott-kerdesek.md), [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md)).

## 5. P3 — belső párbeszéd szerepekkel

- **Cél:** Gondolkodó / Kritikus / Tesztelő / Tanár — „csevegés a helyi AI-okkal”, de csak ahol mérhetően segít.
- **Benne:** szerepek és vita-protokoll, prompt-sablonok, a prefixváltás árának kezelése (mért: e2b ~6 s,
  e4b ~17 s → csoportosított hívások); a szerepkönyv külön modellen, hogy ne törölje a Jarvis meleg
  prefixét ([NK20](03-nyitott-kerdesek.md)); a belső promptnyelv A/B-mérése ([NK18](03-nyitott-kerdesek.md)), ha a P0-ban nem dőlt el.
- **Kész, ha:** a `dev` készleten szerepekkel vs. nélkülük mérve a javítással@3 és a medián idő; a Kritikus
  pontossága (igazolt / összes állítás) mérve. **Ha nem javít, alapból kikapcsolva marad** — ez is eredmény.
- **Kockázat:** két kis modell ugyanabban téved („visszhang”), több CPU-idő → a kapu mindig a teszt, nem a vita.

## 6. P4 — éjszakai önálló tanulás

- **Cél:** a gép szabad idejében Auri gyakorol, ismétel, konszolidál — kérés nélkül is fejlődik.
- **Benne:** tananyag-sorrend, gyakorlás (70% aktuális szint · 20% következő · 10% hibakeresés), ismétlés
  (a tárolt megoldások újrafuttatása modellcsere után is), konszolidáció, időablak + tétlenségi kapu
  (`BACKGROUND` osztály), a heti `heldout` mérés több éjszakára bontva (nyelvenként ~3–8 óra, becslés),
  reggeli összefoglaló; a mai `brainChat.ts` önálló köre (90 s-onként, aktivitástól függetlenül, felhős
  tartalékkal) **kivezetve és kiváltva** ([NK15](03-nyitott-kerdesek.md)).
- **Kész, ha:** 7 éjszaka úgy fut, hogy a felhasználót egyszer sem zavarja (aktivitásra azonnal átadja a
  sávot — mért ok: közös sávon az 1. token medián 3,9 s, p90 14,0 s lett); minden reggel összefoglaló;
  a tananyag-haladás és az ismétlési eredmény a naplóban; audit: 0 személyes adat a tanult elemekben.
- **Kockázat → enyhítés:** rossz dolgot tanul → csak ellenőrzött kerül tárba; zaj, áram, lemez → keret és
  kvóta ([03-nyitott-kerdesek.md](03-nyitott-kerdesek.md) NK5).

## 7. P5 — komplex feladatok

- **Cél:** feladatbontás, terv–végrehajtás–ellenőrzés, többfájlos projektek, önjavítás ([../07-komplex-feladatok/](../07-komplex-feladatok/01-feladatbontas.md)).
- **Benne:** L3–L4; terv-DAG és validálás, checkpoint/rollback, újratervezés, projekt-manifeszt, receptek,
  a teljes példa; S1 sandbox kötelező (csomagok, többfájlos kód); a `web/`-en L4-hez tesztfuttató kell ([NK19](03-nyitott-kerdesek.md)).
- **Kész, ha:** a [teljes példa](../07-komplex-feladatok/05-teljes-pelda.md) 5 futásból ≥ 3-szor emberi
  beavatkozás nélkül zöld (célérték); az E5 készleten (5–8 többfájlos mini-projekt) a sikerarány és a medián idő mérve;
  a rollback hibabeinjektálással, a folytatás a folyamat megölésével tesztelve; a második hasonló feladat mérhetően gyorsabb.
- **Kockázat:** egy feladat 30–60 perc (becslés) CPU-n, egymásra épülő hibák → kis lépések, kapuk, keretek.

## 8. P6 — opcionális felhő-router + kódoló modell + értékelő műszerfal

- **Cél:** a modellválasztás mért adatokon alapuljon; a felhő csak opcionális, tudott segítség.
- **Benne:** router (feladattípus → modell, a naplók alapján); felhős tartalék (Groq, Gemini) titok- és
  PII-szűrővel, 429 → következő szolgáltató; a kódoló modellek rendszeres összemérése; műszerfal a
  fejlődési naplóból (sikerarány modellenként, feladattípusonként, idő). Megjegyzés: a kódoló jelöltek
  **mérése már a P0-ban** megtörténik ([NK3](03-nyitott-kerdesek.md)) — a P6 a rendszeres, automatikus választást adja.
- **Kész, ha:** kikapcsolt felhővel minden működik; bekapcsolt felhővel egy beültetett hamis titok
  egyszer sem hagyja el a gépet (teszt); minden router-döntés indokkal naplózva; a műszerfal ≥ 4 hét trendet mutat.
- **Kockázat:** az ingyenes keretek változnak; a Gemini ingyenes csomagja EGT-felhasználónak nem
  használható (a `chat.ts` csak `GEMINI_PAID=1` mellett hívja); a kimenet tárolhatósága nyitott ([NK4](03-nyitott-kerdesek.md)).

## Kapcsolódó

- [02-kovetkezo-lepesek.md](02-kovetkezo-lepesek.md) · [03-nyitott-kerdesek.md](03-nyitott-kerdesek.md) · [../thinking.md](../thinking.md)
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md) · [../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)
- [../06-programozas/01-cel-es-szintek.md](../06-programozas/01-cel-es-szintek.md) · [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) · [../12-otlettar/01-otletek.md](../12-otlettar/01-otletek.md)
