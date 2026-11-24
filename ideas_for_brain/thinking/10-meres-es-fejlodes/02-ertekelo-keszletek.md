# Értékelő készletek — min mérjük az agyat

> **Miről szól:** a hét kiértékelő készlet (magyar kérdés-válasz, programozási feladatok, eszközhívás,
> hibakeresés, komplex feladatok, biztonság, BRAIN-útválasztás): formátumuk, a fejlesztői és a
> visszatartott (held-out) rész szétválasztása, a szivárgás elleni védelem és a frissítési szabályok.

## 1. Áttekintés

A méretek **tervek (becslés)**; a „Ma” oszlop azt mutatja, mi létezik már.

| Kód | Készlet | Méret | Pontozás | Mikor fut | Fázis | Ma |
|---|---|---|---|---|---|---|
| E1 | Magyar kérdés-válasz | 100 kérdés | automatikus + kézi rubrika (0–2) | havonta, modellcserekor | P1 | nincs |
| E2 | Programozási feladatok = `aurikod-hu` ([../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md)) | v1: TS + Python, L0–L1, nyelvenként ≥ 40 `dev` + ≥ 60 `heldout` | rejtett tesztek a sandboxban | minden ciklus-változtatás után | **P0** | nincs |
| E3 | Eszközhívás (Jarvis) | 30 parancs + 5 csevegő kérdés | `eval_tools.py` | modell- vagy promptváltáskor | megvan | `auri-jarvis/tests/fixtures/eval/tools_hu.yaml` |
| E4 | Hibakeresés | 30 hibás kód + piros teszt | zöldre javítja-e | heti | P0–P3 | nincs |
| E5 | Komplex feladatok | 5–8 többfájlos mini-projekt | elfogadási tesztek + kézi | havonta | P5 | nincs |
| E6 | Biztonság | adatvédelem, titkok, injekció, sandbox, `canLearn` | 0 hiba / 100% | minden kiadás előtt | P0-tól | részben: `web/tests/*.test.ts` |
| E7 | BRAIN-útválasztás | kérdések: „válaszoljon-e a BRAIN” | igaz/hamis | minden változtatás | megvan | `web/tests/brain-answers.test.ts` |

## 2. Formátumok

**E1 — a `tools_hu.yaml` mintájára** (csak fiktív adat):

```yaml
version: E1-v1
items:
  - id: e1-0001
    q: "Mi a különbség a lista és a tuple között Pythonban?"
    expect: { must: ["módosítható", "nem módosítható"], must_not: ["ugyanaz"] }  # normalizált, ékezetfüggetlen
    rubric: nyelv          # kézi 0–2: nyelvhelyesség, természetesség, tömörség
    tags: [python, alap]
    split: heldout
  - id: e1-0002
    q: "Mi Ausztrália fővárosa?"
    expect: { must: ["Canberra"], must_not: ["Sydney"] }   # a facts-sheetben rögzített ismert hiba
    tags: [altalanos, ismert-hiba]
    split: dev
```

**E2 — egy feladat egy mappa** (javasolt hely: `evals/`; a végleges hely a
[../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) szerint):

```
evals/E2/py-017-intervallumok-osszevonasa/
  task.md          # a feladat magyarul — ezt kapja a modell
  meta.yaml        # szint, nyelv, időkorlát, címkék, licenc, split
  public_test.py   # példák, a modell láthatja
  hidden_test.py   # SOHA nem kerül promptba, tudástárba vagy gyakorlókészletbe
  reference.py     # csak annak igazolására, hogy a rejtett teszt helyes (rajta zöld)
```

```yaml
id: py-017
level: 2                 # a szintek: ../06-programozas/01-cel-es-szintek.md
lang: python             # első körben python és typescript
time_limit_s: 10
tags: [lista, rendezés, intervallum]
license: own             # saját írás; külső forrásnál: licenc + link
split: heldout           # dev | heldout
```

**E3 — ami már működik.** Az `auri-jarvis/scripts/eval_tools.py` a valódi Mind-promptot használja
(persona + fiktív profil „Minta Máté” + eszközsémák), a fast-path-et szándékosan kikerüli, csak az
első kört pontozza (eszköz + argumentumok, vagy „nincs eszköz”), eredményét JSON-ba és Markdownba
írja. Kész-feltétele ≥ 85%; mért eredmény `gemma4:e2b`-n 96,7% (LLM) / 100% (fast-path + LLM).
**Ez a minta** a többi készlethez: fixture-YAML + bíráló függvény + géppel olvasható eredmény.

**E6 — biztonsági részkészletek:**

| Rész | Tartalom | Forrás / minta |
|---|---|---|
| E6a adatvédelem | fiktív profil; kijelentkezett munkamenet nem mondhat fel semmit belőle; `isPersonal` pozitív/negatív példák | `brain-answers.test.ts`, `privacy-isolation.test.ts` |
| E6b titkok | jelszó, kulcs, kártya, IBAN, azonosító | `secrets-and-providers.test.ts` |
| E6c injekció | ≥ 30 fiktív oldal, README, kódkomment, hibaüzenet | [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md) |
| E6d sandbox | kártékony próbakészlet | [../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md) |
| E6e tanulási kapu | T1–T9, szabályonként 3 tiltandó + 3 megengedett | [../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md) |

## 3. Fejlesztői (dev) és visszatartott (held-out) rész

- Minden készlet két részre oszlik: **dev** (kb. 40%, becslés) — ezen hangolunk promptot, ezt látják a
  fejlesztők és az implementáló AI-ügynökök; **held-out** (kb. 60%) — csak pontozásra.
- **Szivárgás elleni védelem:**
  1. a held-out feladatszövegek és referenciamegoldások normalizált hash-e a `canLearn` T8-as
     tiltólistáján van — a tudástárba nem kerülhetnek;
  2. az önálló tanulás témasorába nem kerülhetnek ([../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md));
  3. a gyakorlófeladatok ([../06-programozas/08-gyakorlofeladatok.md](../06-programozas/08-gyakorlofeladatok.md))
     **diszjunktak**: egyik sem lehet közeli másolata held-out feladatnak (Jaccard < 0,5, becslés);
  4. AI-ügynök a held-out részen nem hangolhat promptot — ez a szabály itt rögzítve.
- **Nyilvános benchmarkok** (pl. HumanEval, MBPP — a licencet letöltéskor ellenőrizni) csak
  kiegészítő összevetésre jók: valószínűleg benne vannak a modellek tanítóadatában, ezért fő
  mérőszámnak nem használjuk őket.

## 4. Frissítési szabályok

- **Verziózás:** `E2-v1`, `E2-v2`…; eredmény csak azonos verzión belül vethető össze. Minden
  készletmappában `CHANGELOG.md`.
- **Negyedévente** (becslés) 10–20% új elem, elsősorban ott, ahol a valós használat hiányt mutat
  (hiány-statisztika). Új elemet nem a kiértékelt helyi modell ír egyedül: kézi írás vagy felhős segítség,
  de mindig referenciamegoldással és emberi átnézéssel.
- **Telítődés:** ami 3 egymás utáni futáson `pass@1`-gyel zöld, a „regressziós” részhalmazba kerül
  (tovább fut, kisebb súllyal). Ha egy szint 80% fölött telített, nehezebb szint kell.
- **Hibás elem** (rossz teszt): javítás új verzióban, soha nem csendben.
- **Modellcsere:** előbb minden készlet újra lefut az új modellen (új alapérték), csak utána hasonlítunk.
- **Szivárgás gyanúja** (held-out elem vagy közeli másolata a tudástárban, gyakorlókészletben):
  az elem nyugdíjba megy, helyére új jön, új verzió.

## 5. Futtatás

- Csak tétlen gépen (egy Ollama-sáv); `temperature` 0, rögzített `seed`; rögzítjük a modellt, az
  Ollama-verziót és a készletverziót ([01-mit-merunk.md](01-mit-merunk.md), 9. pont).
- Parancsvázlat: `auri-core eval run E2 --split heldout --model <modell>` → JSON-eredmény + rövid
  Markdown-összefoglaló (ahogy az `eval_tools.py` teszi).
- Az E2 teljes futása CPU-n órákig tarthat (becslés: feladatonként percek, ld. a facts-sheetet) →
  éjszakai ablak; napközbeni gyors körhöz a dev-részhalmaz.

## Kész, ha

- a P0 lezárása előtt létezik az `E2-v1` (= `aurikod-hu v1`, nyelvenként ≥ 60 held-out feladat), és mindegyik referencia-
  megoldása zöld a saját rejtett tesztjén;
- a T8 tiltólista él, és teszt bizonyítja, hogy egy held-out feladatszöveget a `canLearn` elutasít;
- az E6 minden kiadás előtt lefut, és 100%-os;
- minden futás géppel olvasható eredményt ír (készletverzió, modell, pontszámok), amit a heti napló felhasznál.

## Kapcsolódó

- [01-mit-merunk.md](01-mit-merunk.md) · [03-fejlodesi-naplo-sablon.md](03-fejlodesi-naplo-sablon.md)
- [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md) · [../06-programozas/08-gyakorlofeladatok.md](../06-programozas/08-gyakorlofeladatok.md)
- [../07-komplex-feladatok/05-teljes-pelda.md](../07-komplex-feladatok/05-teljes-pelda.md) · [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
