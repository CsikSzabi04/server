# Magyar nyelv — toldalékok, számnevek, gyenge kis modell, kétnyelvűség

> **Miről szól:** mi teszi nehézzé a magyart egy kis helyi modellnek és egy kulcsszavas agynak,
> mit mértünk a gemma4:e2b magyarjáról, hogyan segít a determinisztikus előfeldolgozás (pl.
> `hu_text.digitize`), hogyan kezeljük a kétnyelvű (HU/EN) válaszokat és tudást, és hogyan mérjük.

## 1. Mitől nehéz?

| Jelenség | Példa | Következmény |
|---|---|---|
| Toldalékolás (agglutináció) | kód → kód**ot**, kód**ommal**, függvény**ben** | szó szerinti egyezés nem elég; tő kell |
| Ékezet nélküli gépelés | „ki vagy”, „fuggveny”, „hany ora” | ékezettűrő összevetés (`fold` / `norm`) |
| Rövid, kétértelmű szavak | „egy” (névelő / 1), „hét” (7 / week), „hat” (6 / ige), „vagy” ⊃ „agy” | rövid kulcsszó önmagában soha nem dönt |
| Számnevek, idő-toldalékok | „huszonöt”, „nyolc**kor**”, „ötven**et**” | a kis modell félreérti (2. pont) |
| Angol szakszó magyar toldalékkal | „a VS Code-**ot**”, „React-**ben**”, „a `commit`-**ot**” | kötőjeles toldalék levágása (`name_candidates`) |
| Szabad szórend | „a listát rendezd” = „rendezd a listát” | szózsák/tő alapú illesztés, nem sorrend |
| Összetett szavak | „adatbázis-kapcsolat”, „hibakezelés” | a tagokra bontás segít a keresésben |

## 2. Amit tudunk (2026-11-21, `auri-jarvis` mérései és kimenetei)

- **gemma4:e2b magyar csevegése gyenge** — mért példa: „Mi Ausztrália fővárosa?” → „Sydney.”
  (tényhiba); a pontozandó mintákban (`auri-jarvis/data/mind/eval/chat_*.md`) nyelvtanilag döcögő mondatok is
  vannak (pl. „gyorsabb, de volatilissá téve a gép leállásakor”).
- **Számnevek:** a `digitize()` előtt a modell félreértette őket — „huszonöt perces” → 1200 s,
  „holnap reggel nyolckor” → 09:00, „este hétkor” → 10:00 (az `eval_tools` futásából, a `hu_text.py`
  docstringjében rögzítve; a tények közé még nincs felvéve).
- **Utána** (`digitize` + persona-sorrend + in-context minta + pontosabb eszközleírások együtt):
  eszközhívás 96,7% (csak LLM) / 100% (fast-path + LLM) a 30 magyar parancson. Az egyes javítások
  külön hatását nem mértük.

**Következtetés:** (1) amit determinisztikusan meg lehet oldani (számok, toldalékok, ékezetek), azt a
modell **előtt** oldjuk meg; (2) tényt a kis modell ne „tudjon”, hanem **kapjon** (megalapozás,
[01-ertelmes-mondatok.md](01-ertelmes-mondatok.md)); (3) a magyar kimenetet **ellenőrizni** kell.

## 3. Bemeneti oldal: normalizálás a modell és a keresés előtt

```
felhasználói szöveg
  ─▶ nyelvfelismerés      egy közös detectLang (ékezet + funkciószó-szavazás)
  ─▶ digitize()           számnév → szám, csak egyértelmű helyzetben ("huszonöt" → 25, "nyolckor" → "8-kor";
                          "egy kis zene", "jövő héten" érintetlen)
  ─▶ illesztéshez         fold/norm (kisbetű, ékezet nélkül) + szókezdő egyezés ≤ 3 betűs toldaléktűréssel
                          (a knowledge.ts keywordScore szabálya) + name_candidates (tárgyrag, kötőjeles toldalék)
  ─▶ kereséshez           tövesítés (pl. Snowball magyar stemmer vagy Hunspell hu_HU — mérni kell, melyik jobb)
                          + angol változat (bilingualQueries / toEnglishish szótár)
```

- A `digitize()` **Pythonban** van (`auri-jarvis/auri_jarvis/mind/hu_text.py`). Az Auri Core (P1) ezt
  közvetlenül használja, ha Pythonban készül; ha TypeScriptben, portolni kell a teszteivel együtt
  (`tests/mind`), mert a szabályai finomak („Huszöt” fuzzy → 25, de „hát” ≠ 6).
- **Két `detectLang` van:** a `web/src/autolearn/lang.ts` csak ékezetből dönt (a „ki vagy?” így `en`),
  a `web/src/brain/lang.ts` funkciószavakkal is szavaz (a „ki vagy?” → `hu`). A Core-ban **egy**
  közös legyen, a `brain/lang.ts` logikájával és a regressziós eseteivel.
- Vektoros keresésnél az `embeddinggemma` magyar minősége nincs mérve → a P1-ben mérni kell egy kis
  HU kérdés–kártya párkészleten, mielőtt a kulcsszavas illesztést leváltjuk.

## 4. Kimeneti oldal: hogyan legyen jó magyar szöveg?

| Út | Mikor | Költség | Kockázat |
|---|---|---|---|
| **A)** ellenőrzött kártya magyar mondata (`claim_hu`, ahogy a `knowledge.ts` `hu` mezője) | pontosan erre kérdeztek | ~0 | nincs |
| **B)** a modell közvetlenül magyarul fogalmaz a tartalomtervből | rövid válasz (≤ 2–3 mondat) | 1 generálás | döcögő nyelvtan |
| **C)** belső lépések angolul, a végső szöveg magyarul (ugyanabban a munkamenetben) | magyarázat, tanítás, hosszabb válasz | +1 lépés | lassabb |
| **D)** felhős modell a végső megfogalmazáshoz (P6, opt-in, személyes adat nélkül) | hosszú magyarázat, ha a felhasználó kéri | hálózat, kvóta | adatvédelem, elérhetőség |

Alapszabály: **A, ha lehet; különben B rövid válasznál, C hosszúnál.** Hogy a C ténylegesen jobb-e a
B-nél, azt a 6. pont értékelésével kell eldönteni — feltételezés, nem tény.

**Kimeneti ellenőrzések:**
- **Helyesírás:** Hunspell `hu_HU` szótárral a hibás szavak aránya (kód, backtickes szakszó kihagyva).
  Küszöb fölött egy újrafogalmazás. (A küszöböt mérni kell; a szakszavak miatt nem lehet 0.)
- **Szakszó-szótár:** a `bilingual.ts` HU→EN szótárának megfordítása + a „maradjon angolul” lista
  (`commit`, `pull request`, `endpoint`, `merge`). Szakszó angolul, backtickben, **kötőjeles
  toldalékkal**: „a `fetch`-et”, „a `useEffect`-ben”.
- **Tegezés, hangnem:** a persona szerint (Jarvis: higgadt, rövid; AuriGPT: programozó-orientált).

## 5. Kétnyelvűség

- **A válasz nyelve = a kérdés nyelve** (a Jarvis persona szabálya: magyarul, de angolra angolul).
- **Kód:** az azonosítók angolul; a kommentek nyelve beállítás (`code_comment_lang`, alapérték:
  angol, mert a kód így hordozható) — a magyarázat a kód körül a felhasználó nyelvén.
- **Tudás:** minden kártya `claim_en` mezővel készül (a források zöme angol), a `claim_hu` igény
  szerint, lusta módon (első magyar használatkor) születik, és **ugyanúgy ellenőrizzük**, mint a
  többi magyar kimenetet. Keresés kétnyelvűen: `bilingualQueries`.
- **Hangmód:** a számokat a TTS-nek fordított irányban kell kezelni (szám → kimondható alak, ld.
  `say_duration`); a „hybrid” ElevenLabs-mód rögzített mondatai sablonok, nem generált szövegek.

## 6. Értékelés

**HU-50 készlet** (kiinduló összetétel): 10 tény (megalapozással), 10 programozási magyarázat,
10 számnév/idő-kifejezés, 10 ékezet nélküli vagy toldalékos kérdés, 10 vegyes HU/EN szakszavas kérdés.
Fiktív adatokkal, személyes adat nélkül.

| Mérőszám | Hogyan |
|---|---|
| Nyelvhelyesség | a válasz nyelve egyezik-e (automatikus) |
| Helyesírás | hibás szavak / 100 szó (Hunspell) |
| Tényhelyesség | kézi címke vagy a kártyákkal összevetve |
| Természetesség | emberi pontozás 1–5 (a `chat_*.md` mintájára) |
| Számnév-értelmezés | a normalizált érték egyezik-e (automatikus) |

**Kész, ha:** (1) a HU-50 alapmérése megvan gemma4:e2b-vel B és C úton is, és ebből eldől az
alapértelmezett út; (2) a számnév-esetek 100%-a jó a `digitize` után (determinisztikus, tesztelhető);
(3) a „ki vagy?”-típusú ékezet nélküli rövid kérdések nyelvét a közös `detectLang` jól ismeri fel.

## Kapcsolódó

- [01-ertelmes-mondatok.md](01-ertelmes-mondatok.md) · [03-magyarazas-es-tanitas.md](03-magyarazas-es-tanitas.md)
- [../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md](../08-modellek-es-utvonalvalasztas/01-helyi-modellek.md) · [../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md](../08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md)
- [../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md) — kétnyelvű lekérdezés
- [../10-meres-es-fejlodes/02-ertekelo-keszletek.md](../10-meres-es-fejlodes/02-ertekelo-keszletek.md)
- [../00-alapok/03-tenyek-es-meresek.md](../00-alapok/03-tenyek-es-meresek.md)
