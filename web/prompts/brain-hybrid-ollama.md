# PROMPT — Hibrid „erős AI": a saját AGY + egy letöltött OLLAMA-modell EGYÜTT, automatikusan együtt-okosodva

> **Cél egy mondatban:** a helyben épített „literal agy" (Auri BRAIN) és **egy egyszerű, letöltött
> Ollama-modell** (pl. `gemma2:2b`) **egyetlen hibrid elmeként** működjön: az agy **megalapozza
> (grounding)** a modell minden válaszát a saját tudásával, a modell pedig **megtanítja az agyat**
> (desztilláció) minden válaszával — így együtt sokkal erősebbek, mint külön, és az agy **magától,
> folyamatosan okosodik**, miközben a modell-függés idővel csökken (emelkedő autonómia).
>
> Ez a prompt a MEGLÉVŐ kódra épül (nem nulláról). Az implementáló feladata összekötni a két felet a
> lent leírt két irányban (grounding + desztilláció), egy hibrid arbiterrel és egy önálló tanuló loop-pal.

---

## 0. Ami MÁR megvan (erre építünk, ne írd újra)

**A helyi agy — `web/src/brain/**`:**
- `learn.ts` — `BrainLearner`: szókincs (`words`, count/firstSeen/lastSeen/sources), Markov-átmenetek
  (`transitions`) + **kétirányú index** (`reverse`, `neighbors(word)` = mi mivel van összekötve, µs alatt),
  karaktermodell (`charFreq/charNext`, `babble`), Q→A minták (`qa`, `recall`), `respond`, `consolidate`
  (M4), `ingestTokens` (gyors tömeges út), `toState`/`from` (a `bulk:*` szavak NEM perzisztálnak).
- `seedCorpus.ts` — `applyBaseSeed` (ábécé, EN/HU/DE társalgás, `knowledge.ts` ~140 téma, `relations.ts`
  kapcsolati tudás, programozási chunkok), `seedIngestedCorpora` (dinamikus import: `programming.ingested`
  ~392 chunk + `general.ingested` ~1122 Wikipedia-chunk), `SEED_VERSION` (verzió-augment).
- `answer.ts` — `composeLocalAnswer(learner, query, facts)`: PRIORITÁS recipe(kód-sablon) → snippet+forrás
  → `findKnowledge` (tiszta mondat a nyelven) → `recall` (tanult Q→A) → személyes tény → web-doc → doc-link
  → '' (üres → a hívó modellre vált). `findKnowledge/findSnippet/findRecipe`, `pickFacts`.
- `arbiter.ts` — `decideRoute(ctx)` → `'retrieval' | 'local-brain' | 'local-model' | 'fallback'` +
  `isLocalBrainReady`, `arbiterContext`.
- `useBrainLearning.ts` — EGY megosztott `BrainLearner` singleton; aszinkron hidratálás IndexedDB-ből
  (`brainStore`, gyors debounce-olt mentés); `bulkVocab` (1M procedurális prog-szó) + `selfBuild`
  (önépítő: összekötött klaszterek + magányos „golyók" + 700k adat, `bulk:self`, nem perzisztált);
  **Stage 6** (`stage6/net.ts` — tfjs, lusta import, tanulási görbe); hook-API: `state, observe(u,a),
  reset, speak, babble, recentWords, reply, covers(q,facts), learnWeb(q,hits,pages), stage6()`.
- `web.ts` + `webStore.ts` — web-tanulás loop: `ingestWeb` (region:web doc + observe), `brainCovers`,
  `topCoveringWebDoc` (IndexedDB-perzisztált).
- `graph.ts` + `useBrainGraph` — a 3D `/brain` adat (régiók, csomópontok, élek, `neighbors`).
- `contracts.ts` — közös típusok (BrainNode/Edge/Region, BrainState, WebHit/WebDoc, Stage6Status, …).

**A modell-út:**
- `web/src/lib/api.ts` → `streamChat(messages, handlers, signal, opts)` → SSE `data:{delta}` / `{usage}`.
- `web/api/chat.ts` (proxy) — provider-lánc: **(1) lokális Ollama** (`AURI_SERVER_URL` tunnel,
  `/health` próba + `/v1/chat`, csak ha a PC megy), **(2) Groq**, **(3) Gemini**. `X-Auri-Source` fejléc
  jelzi, ki válaszolt (`ollama`/`groq`/`gemini`). Letöltött modellek (D:\Server\PublicFreeAI\Ollama):
  `gemma2:2b` (alap), `qwen2.5:1.5b`, `smollm2`, `tinyllama`.
- `web/src/brain-bridge/brainChat.ts` — híd: `localAnswer` = brain-first (`covers()` → offline válasz,
  vagy `null` → modell), `learnWebHits` = `learnWeb`, `observeTurn` minden kör után.
- `web/src/lib/memory.ts` (régi, csak olvasható) — `systemMessage(query)` = persona + profil +
  releváns emlékek injektálása a modellnek (RAG-csíra).
- `src/autolearn/**` — minőségi réteg: `processHits/rerankSmart/rerankDev`, `extractKeyContent`
  (oldal-lényeg kivonat), `domainTrust`, `circuitBreaker`, `bilingual`.

**Jelenlegi viszony:** brain-VAGY-modell (brain-first, modell-fallback). **Hiányzik:** hogy EGYÜTT
dolgozzanak (grounding) ÉS hogy az agy a modellből tanuljon (desztilláció). EZT kell megépíteni.

---

## 1. A két szerep (őszinte munkamegosztás)

- **AGY** = memória + visszakeresés + asszociációk + tudásbázis + offline válasz arra, amit lefed.
  Gyors, offline, kulcs nélkül. NEM tud tetszőleges, folyékony szöveget generálni.
- **OLLAMA-MODELL** (`gemma2:2b`…) = folyékony fogalmazás/érvelés. Kell hozzá a bekapcsolt PC. Magától
  NEM ismeri a felhasználót/az adatait — kontextust kell kapnia.
- **EGYÜTT** = az agy ad **megalapozó kontextust** (tények, kapcsolatok, kód-snippet, forrás) → a modell
  **abból** ír folyékony, megalapozott választ → az agy **megfigyeli és tanul** a válaszból → legközelebb
  többet fed le maga. Ez a hibrid a lényeg: a kis modell az agy tudásával „okosabbnak" hat, az agy pedig
  a modell folyékonyságából desztillál tudást.

---

## 2. Amit építeni kell (komponensek)

### A) AGY → MODELL: grounding (RAG a helyi aggyal)
Új `web/src/brain/grounding.ts` → `buildBrainContext(query, memories): string`.
A modell-hívás ELŐTT állítson össze egy tömör, **token-budgetelt** „BRAIN KNOWLEDGE" blokkot a query alapján:
- a legrelevánsabb `findKnowledge` tény(ek) (a kérdés nyelvén),
- programozási kérdésnél a `findSnippet`/`findRecipe` kód + hivatalos forrás-URL,
- a web-tanult `topCoveringWebDoc` lényege + forrás-link,
- a **kapcsolódó fogalmak**: `learner.neighbors(queryTerms)` → „X összefügg Y/Z-vel" (asszociációk),
- a `pickFacts(memories, query)` személyes tények + a `recall(query)` tanult Q→A, ha van.
A blokk a meglévő `systemMessage` MELLÉ/UTÁN kerül a system üzenetbe, ezzel az utasítással a modellnek:
„A BRAIN KNOWLEDGE blokk valódi, megalapozott tudás — ezt használd igazságként, idézd a forrásokat,
maradj konzisztens vele; ha hiányos, mondd ki." Cél: a kis modell a saját agyunk tudásából válaszoljon.

### B) Hibrid routing (az arbiter kibővítése)
`arbiter.ts` — új viselkedés/route:
- **`local-brain`** (agy egyedül): ha az agy magabiztosan, teljesen lefedi (knowledge/recipe/snippet/recall)
  → azonnali, offline, modell NÉLKÜL. (Már létezik.)
- **`brain+model`** (ÚJ, a „együtt" mag): ha az Ollama elérhető → a modellt hívd a **brain-context
  blokkal** (megalapozott generálás). Ez az alapértelmezett „együtt" mód, valahányszor a PC megy és a
  kérdés nyitott/összetett.
- **`model`/`fallback`**: tiszta modell/Groq/Gemini, ha az agy-kontextus vékony.
Logika: tényszerű/kód-kérdésre, amit az agy fed → brain-alone (gyors, offline); nyitott/összetettre →
brain+model. Az arbiter adjon vissza route-ot + confidence-t (a meglévő `ArbiterDecision`).

### C) MODELL → AGY: desztilláció (automatikus együtt-okosodás)
Új `web/src/brain/distill.ts` → `distill(query, answer, source)`.
MINDEN modell-válasz után (bármelyik provider) az agy desztillálja:
- `learner.observeTurn(query, answer)` → szókincs + Markov + Q→A nő (részben már megvan a hídban),
- `extractKeyContent(answer, query)` (autolearn) → a válasz LÉNYEG-mondatait tartós tudásként/Q→A-ként
  tárolja (pl. egy „learned" knowledge-tételként vagy a `qa`-ba), hogy LEGKÖZELEBB a modell NÉLKÜL is
  megválaszolja,
- a (query→answer) pár a **Stage 6 háló** tanító-mintája lesz (inkrementális),
- frissítse az **autonómia-mérőt** (mennyit fed már le maga az agy).
Ez offline **knowledge distillation**: a kis modell „tanárként" tölti fel az agyat; minél többet
chatelsz, annál többet tud az agy MAGÁTÓL → emelkedő autonómia, csökkenő modell-függés.

### D) Önálló tanuló loop („tanulj magadtól, amíg ráérsz")
Korlátozott háttér-folyamat (rate-limitelt, csak ha Ollama megy + `auri.brain.selfStudy` flag BE):
- az agy megtalálja a GYENGE pontjait: magányos (él nélküli) koncepció-csomópontok, gyakori user-témák
  vékony lefedettséggel, nemrég NEM-lefedett kérdések (naplózva `recordCoverageGap`),
- ezekre kérdez a lokális modelltől (pl. „Mi az X és mivel függ össze?") — kevés/perc, alacsony prioritás,
- desztillálja a választ (C) → kitölti a réseket, **összeköti a magányos golyókat**, bővíti a tudást.
Így az agy „magától tanul" a modellt tutornak használva, az autonómia automatikusan nő. Korlátos +
flag-mögötti (nincs elszállás, nincs túl-hívás; a rate-limit/circuitBreaker az autolearnből újrahasznosítható).

### E) Modell-választás + állapot
- Az aktív letöltött Ollama-modell kiválasztható (alap: `gemma2:2b` mint „az egyszerű modell");
  a `ModelPicker`/UI mutassa, melyik fut.
- A `/brain` mutassa: melyik elme felelt (`brain` / `brain+model` / `model`), az **autonómia %** (emelkedik),
  a desztilláció-számláló („learned from model: N"), és a Stage 6 tanulási görbe.

### F) Őszinteség / korlátok
- Ollama csak bekapcsolt PC-vel (health-próba); ha kikapcsolt → agy-only + Groq/Gemini fallback, nincs összeomlás.
- Az agy EGYEDÜL nem éri utol a modellt; az ERŐ a grounding + desztilláció EGYÜTT.
- A desztilláció a modell tudását offline halmozza az agyba — a használat teszi okossá.

---

## 3. Konkrét fájl-feladatok (összefoglaló)

| Fájl | Mit |
|---|---|
| `brain/grounding.ts` (ÚJ) | `buildBrainContext(query, memories)` → tömör grounding-blokk (knowledge+snippet+webdoc+neighbors+facts+recall), token-budget |
| `brain/distill.ts` (ÚJ) | `distill(query, answer, source)` → observeTurn + extractKeyContent → tartós knowledge/Q→A + Stage6-minta; `recordCoverageGap(query)` |
| `brain/arbiter.ts` | +`'brain+model'` route + a fenti logika |
| `brain/useBrainLearning.ts` | expose `ground(query)`, `distill(...)`; háttér `startSelfStudy()` (rate-limitelt, flag) |
| `brain-bridge/brainChat.ts` + `App.tsx` | modell-hívás ELŐTT `buildBrainContext` a system-be; modell-válasz UTÁN `distill(...)`; az arbiter `brain+model`-jét bekötni |
| `brain-view/**` (UI) | autonómia %, „learned from model: N", which-mind badge, Stage 6 görbe |
| (proxy) `api/chat.ts` | NEM kell változtatni — a grounding a system-üzenet része |

---

## 4. Elfogadási kritériumok
1. Ollama bekapcsolva: a válasz FOLYÉKONY (modell) ÉS MEGALAPOZOTT az agy tudásából (idézi az agy
   tényeit/forrásait); minden válasz után az agy szókincse/Q→A/autonómiája NŐ.
2. Ha egy témáról chateltél, később UGYANAZT a kérdést az agy EGYEDÜL (offline) válaszolja meg → a
   desztilláció működött.
3. Az autonómia % emelkedik egy session alatt.
4. Ollama kikapcsolva: agy-only + Groq/Gemini, nincs hiba.
5. `npx tsc --noEmit` + build ZÖLD; nincs új függőség (a tfjs már telepítve a Stage 6-hoz).
6. A grounding token-budgetelt (nem fújja fel a promptot); a self-study korlátos + flag-gated.

## 5. Őszinte kockázatok
- Kis modell (2B) korlátos — a grounding + desztilláció emeli a súlycsoport fölé.
- A desztilláció a modell hibáit is átviheti → maradjon javítható (szerkeszthető memória, felejtés/decay).
- A RAM/perf már nehéz (~1,7M szó) → a grounding maradjon tömör, a self-study korlátos.

---

## 6. Megépítési sorrend (mérföldkövek)
1. **H1 — Grounding:** `buildBrainContext` + bekötés a modell-hívás system-üzenetébe (azonnali minőség-ugrás:
   a kis modell a mi tudásunkból válaszol, forrásokkal).
2. **H2 — Desztilláció:** `distill` minden modell-válasz után (az agy tanul a modellből; autonómia-mérő).
3. **H3 — Hibrid arbiter:** `brain+model` route + which-mind badge a `/brain`-en.
4. **H4 — Önálló tanuló loop:** `startSelfStudy` (a modell mint tutor, gyenge pontok feltöltése, golyók
   összekötése) — flag mögött, rate-limitelt.
5. **H5 — Stage 6 a hurokban:** a (query→answer) párokon a tfjs-háló is tanul → folyékonyabb helyi fogalmazás.

> Minden mérföldkő önmagában is értéket ad, és egyik sem töri a meglévő chatet (flag + fallback).
> A végeredmény: egy **kis, letöltött modell + a mi folyamatosan okosodó agyunk = egy meglepően erős,
> offline-felé húzó, önfejlesztő AI**, pontosan a BRAIN.md autonómia-víziója szerint.
