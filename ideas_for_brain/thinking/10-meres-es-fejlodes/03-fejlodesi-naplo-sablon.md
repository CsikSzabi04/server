# Fejlődési napló — heti sablon és egy kitöltött példa

> **Miről szól:** egy kitöltésre kész heti napló, amiből hétről hétre látszik, hogy az agy tényleg
> javul-e: számok az előző héthez képest, mi változott, mit tanult magától, mi romlott el, mi a
> tanulság, és mi a jövő heti mérhető cél. A végén egy kitöltött példa a 2026/47. hét valós eseményeiből.

## 1. Kitöltési szabályok

- **Hetente egy bejegyzés**, javasolt hely: e fájl mellett egy `naplo/` mappa, hetente egy fájl
  (`naplo/2026-W48.md`). Legfeljebb egy képernyőnyi.
- A számok az eseménynaplóból és a kiértékelések eredményfájljaiból jönnek
  ([01-mit-merunk.md](01-mit-merunk.md)) — kézzel nem „kerekítünk szebbre”.
- Becslés csak „(becslés)” jelöléssel; ami nincs mérve: „—”.
- **Személyes adat és felhasználói szöveg nem kerülhet bele.** Incidensnél is fiktivizált leírás.
- Csak azonos készletverzió és modell számai kerülnek egy sorba; ha változott, a „Környezet” rész mondja meg.
- Kitöltheti ember vagy AI-ügynök; a „kitöltötte” mező kötelező.

## 2. A sablon

```markdown
## <ÉÉÉÉ>/<hét>. hét (<hétfő> – <vasárnap>) · fázis: P<n> · kitöltötte: <név / AI-szerep>

### Környezet
| Modell(ek) | Ollama | Készletverziók | Eltérés (terhelés, hardver, beállítás) |
|---|---|---|---|
|  |  |  |  |

### Számok
| Mérőszám | Előző hét | E hét | Változás | Megjegyzés |
|---|---|---|---|---|
| pass@1 (E2) |  |  |  |  |
| javítással@3 (E2) |  |  |  |  |
| Idő a zöldig, medián (s) |  |  |  |  |
| Válaszhelyesség (E1) |  |  |  |  |
| Eszközhívás (E3) |  |  |  |  |
| BRAIN-útválasztás (E7) |  |  |  |  |
| Agy-találati arány |  |  |  | + helyesség-szúrópróba |
| Elkerült felhőhívás |  |  |  |  |
| Első token, medián / p90 (s) |  |  |  |  |
| Ellenőrzött tudáselemek (+új) |  |  |  |  |
| Tudás-precizitás (szúrópróba) |  |  |  | havonta |
| Háttér-zavarás, Δ medián (ms) |  |  |  |  |
| Biztonság (E6) |  |  |  | csak 100% elfogadható |

### Mi változott (kód, prompt, modell, tudás)
- 

### Önálló tanulás (a napi jelentések összesítése)
- Éjszakák: … · munkaidő: … · egységek: … · jelöltek → ellenőrzött / karantén / elvetett: … · megszakítások: …

### Regressziók
| Elem | Készlet | Mi romlott | Ok | Teendő |
|---|---|---|---|---|

### Incidensek (adatvédelem, biztonság)
- nincs / rövid, fiktivizált leírás + a regressziós teszt neve

### Tanulságok (legfeljebb 3)
1. 

### Jövő hét (legfeljebb 3 cél, mindegyik mérhető)
1. … — Kész, ha …

### Nyitott kérdések (→ ../11-utemterv/03-nyitott-kerdesek.md)
- 
```

## 3. Kitöltött példa — 2026/47. hét

Valós események a `BRAIN_BUILD.md` és a `JARVIS_BUILD.md` naplójából; a mért számok a
[../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)-ből. A gondolkodó agy még
nem létezik, ezért sok sor üres („—”) — ez így őszinte.

**2026/47. hét (11-16 – 11-22) · fázis: P0 előtt · kitöltötte: példa (dokumentáció)**

| Modell(ek) | Ollama | Készletverziók | Eltérés |
|---|---|---|---|
| `gemma4:e2b` (Jarvis), `gemma4:e4b`, `qwen3.5:4b` (összevetés) | 0.40.16, `NUM_PARALLEL=1` | E3: `tools_hu.yaml` (30 + 5); E7: `brain-answers.test.ts` | a Jarvis-mérések egy része egyidejű evallal torzult (ld. tanulságok) |

| Mérőszám | Előző hét | E hét | Változás | Megjegyzés |
|---|---|---|---|---|
| pass@1 / javítással@3 (E2) | — | — | — | E2 még nincs (P0) |
| Eszközhívás (E3), `gemma4:e2b` | — | 96,7% (LLM) / 100% (fast-path + LLM) | első mérés | a kész-feltétel ≥ 85% |
| Első token, `gemma4:e2b` | — | 0,44 / 0,52 s | első mérés | terheletlenül, független kérdés |
| BRAIN-útválasztás (E7) | a régi kódon 5 teszt piros | zöld | javítás | a 21 jó kérdés találata változatlan |
| Biztonság (E6a, adatvédelem) | — | az új PRIVACY-teszt zöld | új teszt | fiktív „Teszt Elek” |
| Agy-találati arány | — | — | — | böngészőnként van, nem összesítjük még |

**Mi változott:**
- `knowledge.ts`: kulcsszó csak szó elején illeszkedik, és csak akkor válaszol, ha a kérdés tényleg a
  témáról szól („ki vagy?” már nem az emberi testről szól); `lang.ts`: ékezet nélküli magyar felismerése.
- Adatvédelem: `isPersonal()` kapu a tanulásban; a vendégprofil csak memóriában; identitásváltáskor
  friss agy; `pickFacts` csak valódi átfedésnél ad kitűzött emléket.
- Jarvis: az `eval_tools.py` alapján a `gemma4:e2b` lett a végleges modell.
- Elindult a gondolkodó agy terve (`ideas_for_brain/thinking/`).

**Önálló tanulás:** nem futott (`auri.brain.selfStudy` alapból KI; ütemező még nincs).

**Regressziók:** nem ismert.

**Incidensek:** 2026-11-20 — kijelentkezve a BRAIN felmondta a felhasználó profilját. Javítva,
regressziós teszt: `web/tests/brain-answers.test.ts` (PRIVACY). Részletek:
[../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md).

**Tanulságok:**
1. Szóhatár nélküli kulcsszó-illesztés téves témát ad („v**agy**” ⊃ „agy”, „b**rain**” ⊃ „rain”).
2. Mérés alatt semmi más ne fusson az Ollamán: egy sáv van, az egyidejű eval a Jarvis számait torzította.
3. Minden új tanulási útnál kötelező az adatvédelmi kapu, és tesztben csak fiktív adat lehet.

**Jövő hét (példa):**
1. Az `E2-v1` első 10 Python-feladata referenciamegoldással — Kész, ha mind zöld a saját rejtett tesztjén.
2. Minimális sandbox — Kész, ha a kártékony próbakészlet ([../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md](../09-biztonsag-es-adatvedelem/03-kodfuttatas-veszelyei.md)) mind a 10 próbája elnyelve.
3. `canLearn()` váz a meglévő `isPersonal` + `containsSecret` szűrőkkel — Kész, ha a `distill` is ezen megy át.

**Nyitott kérdések:** van-e WSL2/Docker a gépen (sandbox); írhat-e vendég munkamenet a közös tudástárba.

## Kapcsolódó

- [01-mit-merunk.md](01-mit-merunk.md) · [02-ertekelo-keszletek.md](02-ertekelo-keszletek.md)
- [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md) (napi jelentés → heti összesítés)
- [../11-utemterv/02-kovetkezo-lepesek.md](../11-utemterv/02-kovetkezo-lepesek.md) · [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)
