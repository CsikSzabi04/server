# Tanulási források — honnan tanul az agy, mit ad, mit kockáztat

> **Miről szól:** az agy nyolc forrásból tanulhat. Itt van, hogy melyik mit ad (főleg a
> programozáshoz), mennyire bízunk benne alapból, mi a kockázata, és milyen kapun kell átmennie,
> mielőtt bármi a tudástárba kerül. A tiltásokat a [05-mit-nem-szabad-megtanulni.md](05-mit-nem-szabad-megtanulni.md) írja le.

## 1. Alapelv: minden forrás csak *jelöltet* ad

Egyik forrás sem ír közvetlenül a tudástárba. Ami bármelyikből jön, abból **jelölt** (`Candidate`)
lesz. Ez átmegy a tiltó kapun (`canLearn`), karanténba kerül, és csak ellenőrzés után lesz `verified`
([04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)).

```
forrás ─▶ kivonás (állítás / snippet / tanulság) ─▶ canLearn() ─▶ karantén ─▶ ellenőrzés ─▶ tudástár
                                                     │ tilos                    │ elbukik
                                                     ▼                          ▼
                                       eldobva (csak egy számláló nő)    elvetve + a kudarc is tanulság
```

```ts
type SourceKind = 'conversation' | 'doc' | 'web' | 'own-code' | 'model' | 'self-study' | 'failure' | 'seed';

interface Candidate {
  source: SourceKind;
  kind: 'fact' | 'snippet' | 'api-note' | 'lesson' | 'error-fix';
  text: string;                    // az állítás, a kód vagy a tanulság
  topic: string;                   // pl. 'python/asyncio', 'react/hooks'
  scope?: { lib: string; range: string };          // verzióhoz kötött tudás (ld. 03-as fájl)
  provenance: { url?: string; file?: string; taskId?: string; model?: string;
                license?: string; fetchedAt: string };
  baseTrust: number;               // a forrás kiinduló bizalma (2. pont), 0..1
  taint: 'user' | 'doc' | 'web' | 'tool' | 'model'; // honnan jött a szöveg (prompt-injekció ellen)
}
```

## 2. A források áttekintése

A „kezdő bizalom” **tervezési kiindulóérték (becslés)**, a mérések alapján hangoljuk.

| # | Forrás | Mit ad a programozáshoz | Kezdő bizalom | Fő kockázat | Fázis |
|---|---|---|---|---|---|
| 1 | Kudarcok, tapasztalatok | mi **nem** működik és miért; javítási minták | 0,9, ha futtatás igazolja | túláltalánosítás | **P0** |
| 2 | Hivatalos dokumentáció | API-k pontos viselkedése, verziókülönbségek | 0,8 | elavulás, licenc | P2 |
| 3 | Kurált seed | alap snippetek, receptek, hivatalos linkek | 0,8 | elavulás | megvan |
| 4 | Saját kód (a felhasználó projektjei) | a felhasználó stackje, konvenciói, bevált minták | 0,6 | titok a kódban, magánkód kiszivárgása | P1 |
| 5 | Web (nem hivatalos) | megoldásminták, hibaüzenetek magyarázata | 0,4–0,65 (`domainTrust`) | téves vagy régi tartalom, injekció, licenc | P2 |
| 6 | Modellválasz (lepárlás) | magyarázat, vázlat, ötlet | 0,3 | **hallucináció** | megvan, P0-tól karanténnal |
| 7 | Önálló tanulás | a tananyag mélyítése, hiánypótlás | 0,3 (ellenőrzés után nő) | hallucináció, CPU-idő | P4 |
| 8 | Beszélgetések | mit kérdeznek valójában → **hiányok**, javítások | 0,3 | személyes adat, titok | megvan (szűrve), P1 |

## 3. Forrásonként

**1. Kudarcok és tapasztalatok.** Minden sandbox-futás nyom: a hibaüzenet, a javítás és a zöld teszt
együtt egy `error-fix` jelölt („`TypeError: 'NoneType' object is not subscriptable` → a függvény nem
adott vissza értéket”). Ez a legértékesebb forrás, mert **gépileg ellenőrzött**. Kockázat: egyetlen
esetből általános szabályt gyártani. Ezért a tanulság csak 2–3 hasonló eset után lesz `lesson`, addig
`error-fix` marad (a konszolidáció vonja össze, ld. [03-ismetles-felejtes-konszolidacio.md](03-ismetles-felejtes-konszolidacio.md)).

**2. Hivatalos dokumentáció.** A `trust.ts` `HIGH` listája (MDN, python.org, nodejs.org, react.dev…)
1,0 domain-bizalmat ad. Mindig **verzióval** tároljuk (`scope`), mert a doksi a legújabb verziót
írja le. Licenc: kivonatot, rövid idézetet és linket tárolunk, teljes oldalt nem.

**3. Kurált seed.** `web/src/brain/seed/programmingCurated.ts`, `recipes.ts`, `sources.ts`. Ma ez a
legtisztább tudás, de nincs rajta verzió és licenc mező. A `programming.ingested.ts` nyers, menüszöveggel
teli oldalkivonat, licenccímke nélkül — ezt P1-ben át kell nézni (ld. [05-mit-nem-szabad-megtanulni.md](05-mit-nem-szabad-megtanulni.md)).

**4. Saját kód.** A felhasználó projektjei (Auri, CliMarkAI) a legjobb minták arra, *ahogy ő*
programoz. Szabály: csak a gazda fiókjában él, **soha** nem kerül seedbe vagy felhőbe ellenőrzés
nélkül; `.env`, `*.key`, `secrets*` fájlokat be sem olvasunk; minden fájl átmegy a `containsSecret`-en.

**5. Web.** A keresés–olvasás–bizalom láncot a [../03-web-szorfozes/](../03-web-szorfozes/01-kereses.md) írja le.
Itt csak annyi: a webes szöveg **adat, nem utasítás**, és egy forrás önmagában nem elég (két független
domain egyezése vagy futtatás kell).

**6. Modellválasz.** Ma a `distill.ts` minden modellválasz lényegét Q→A-ként eltárolja — ellenőrzés
nélkül. A gondolkodó agyban ez **jelölt** lesz 0,3-as bizalommal. A kis modellek mért gyengesége
(„Ausztrália fővárosa: Sydney”, ld. [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)) pont ezt indokolja.

**7. Önálló tanulás.** Ma a `selfStudy.ts` egy 60 témás, fix listát forgat (46 programozási, 14
általános), és a modell 2–4 mondatos magyarázatát ellenőrzés nélkül lepárolja. A gondolkodó agyban a témák a
tananyagból, a hiányokból és a kudarcokból jönnek ([02-ejszakai-onallo-tanulas.md](02-ejszakai-onallo-tanulas.md)).

**8. Beszélgetések.** Nem a tartalmuk a fő érték, hanem a **jel**: mit kérdeztek, amire az agy nem
tudott válaszolni (ment a webre vagy a modellhez), és hol javította ki a felhasználó a választ
(„nem, ez rossz”). Kapu: `isPersonal()` + `containsSecret()` — ma is így van a `useBrainLearning`
`observe` és `distill` útján.

## 4. Mit kell változtatni a mai kódon

| Mai viselkedés | Probléma | Új viselkedés |
|---|---|---|
| `distill.ts`: modellválasz → azonnal Q→A | hallucináció tudássá válik | jelölt, karantén, 0,3 bizalom |
| `selfStudy.ts`: fix lista, nem reagál a hiányokra | nem a fő célt szolgálja | témasor: tananyag + hiány + kudarc |
| seed: nincs `license`, `scope` | licenc és verzió nem követhető | kötelező mezők P1-től |
| a web-tudás `observe`-val a szókincsbe megy | nincs állítás-szint, nincs ellenőrzés | állítás + forrás + bizalom |

## 5. Prioritás a fő cél (programozás) szerint

1. Kudarcok → 2. Hivatalos doksi → 3. Saját kód → 4. Kurált seed → 5. Web → 6. Modell → 7. Beszélgetés.
Ha a tanulási keret szűkös (CPU, egy Ollama-sáv), ebben a sorrendben kapnak időt.

## Kész, ha

- minden tanulási útvonal egyetlen `ingestCandidate(c: Candidate)` függvényen megy át (nincs
  „mellékbejárat” a tudástárba);
- minden tárolt elemnek van `source`, `provenance`, `baseTrust`; webesnek és doksinak `license` is;
- a `distill` és a `selfStudy` kimenete csak karanténba írhat (teszt bizonyítja);
- a forrásonkénti számlálók (jelölt / elfogadott / elvetett / tiltott) megjelennek a mérésekben
  ([../10-meres-es-fejlodes/01-mit-merunk.md](../10-meres-es-fejlodes/01-mit-merunk.md)).

## Kapcsolódó

- [02-ejszakai-onallo-tanulas.md](02-ejszakai-onallo-tanulas.md) · [04-tudas-ellenorzese.md](04-tudas-ellenorzese.md) · [05-mit-nem-szabad-megtanulni.md](05-mit-nem-szabad-megtanulni.md)
- [../03-web-szorfozes/04-tanulas-a-webbol.md](../03-web-szorfozes/04-tanulas-a-webbol.md) · [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md)
- [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) · [../06-programozas/07-sajat-projektekbol-tanulas.md](../06-programozas/07-sajat-projektekbol-tanulas.md)
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
