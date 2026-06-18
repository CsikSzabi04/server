# PROMPT — BRAIN AUTO-LEARN (minden üzenet → agyba mentés + web-keresés + agy-ellenőrzés + tárolás)

> Ez a prompt egyszerre **viselkedés-szerződés** (mit csináljon az Auri-agy minden üzenetnél) és
> **build-spec** (hova, melyik valós fájlba kösd be). Olvasd a `web/BRAIN.md` (I. + II. rész) és a
> `web/BRAIN_BUILD.md` után. Aranyszabály változatlan: a meglévő kódba csak a kijelölt integrációs
> ponton nyúlsz, a tanuló motor `web/src/brain/**`, a perzisztencia `brainStore.ts`/`brain_state.sql`.

---

## 0. A cél egy mondatban

**Bárhol az appban**, ha a felhasználó **kérdez vagy mond valamit**, az agy: (1) **elmenti a kérdést**,
(2) **megnézi a saját agyát** (memória + tanult tudás), (3) ha nincs meg → **rákeres a neten,
linkekkel**, (4) **eltárol mindent** (linkek, szavak, részletek, összefoglaló), és (5) **válaszol** a
forrás-linkekkel — így **minél többet használják, annál okosabb lesz**. Ami ma web-keresés volt, az
holnap már az agyból jön, kulcs és keresés nélkül.

Ez NEM a modell újratanítása (nem fine-tuning), hanem a meglévő **memória + kontextus-injektálás**
(`BRAIN.md` I. rész) kibővítése egy **web-augmentált tanuló hurokkal**. A tanult web-tudás ugyanúgy
`doc`/`summary`/`keyword` emlékként kerül a memóriába, ezért a `relevantMemories`/`pickFacts`
automatikusan visszahúzza a következő kérdésnél — nincs új visszakeresési út, csak új **forrás**.

---

## 1. A hurok (minden bejövő üzenetre, kérdés VAGY kijelentés)

> A számozott lépések a tényleges adatfolyamhoz illeszkednek (`App.tsx` `send` → `useMemory` +
> `brain-bridge/brainChat.ts`). A „[fájl]" jelzi, hova kötöd.

1. **CAPTURE — mentsd a nyers üzenetet.** Minden bejövő `query`-t (kérdés és kijelentés is) rögzíts
   egy könnyű **`query`-emlékként** (forrás=`'chat'`, kis `weight`). Ez az agy „mit kérdeztek tőlem"
   naplója; a meg nem válaszolt kérdés egy **tudás-rés (gap)**, amit a 3. lépés tölt fel.
   → `memStore.addMemory(...)` + a kulcsszavakat a meglévő `ingest` úgyis kinyeri (`extractKeywords`).

2. **RECALL — nézd meg az agyat ELŐSZÖR.** Fusson a meglévő retrieval:
   `memory.relevantMemories(query)` (top-8, pinned/súly/kulcsszó-átfedés + `doc/summary` +3 bónusz)
   **és** a literal-agy: `useBrainLearning().reply(query, pickFacts(memories, query))` /
   `learner.recall(query)`.
   - Ha az agy **lefedi** (erős átfedés, `decideRoute` → `'retrieval'` vagy `'local-brain'`):
     **válaszolj belőle**, ne keress feleslegesen. Jelöld a forrást (mely tény/doc).
   → `web/src/brain/arbiter.ts` (`decideRoute`, `arbiterContext`, `isLocalBrainReady`),
     `web/src/brain/answer.ts` (`composeLocalAnswer`, `pickFacts`).

3. **SEARCH — csak ha az agy NEM fedi (gyenge lefedettség).** Keress rá a neten a `query`-re, és
   gyűjtsd a top találatokat: `{ title, url, snippet }[]` (3–6 forrás elég).
   → ÚJ, szerveroldali végpont kell (lásd 4. szakasz): `web/api/search.ts`, a kulcs a szerveren
     marad — **soha a kliensben** (pont mint a `api/chat.ts` provider-láncánál).

4. **STORE — tárolj el MINDENT a találatokból (ettől nő az agy).** Minden releváns forrásból:
   - **`doc` emlék** a `snippet`-tel, `source = url` → a `relevantMemories` +3 bónusza és a
     `pickFacts` (ami `kind==='doc'|'summary'|'fact'`) **automatikusan** visszahúzza később.
   - **`summary` emlék** a top 1–2 forrásról (best-effort, a `files.ts` `summarizeWithModel`
     mintájára, ha van backend) → tömör, idézhető tudás.
   - **`keyword` emlékek** a `extractKeywords(title + snippet)`-ből, `bumpWeight`-tel a
     visszatérőkre → a téma „erősödik" és gyakrabban kerül kontextusba.
   - **a LINKEK külön megmaradnak**: minden web-eredetű emlék `source`-ában az URL, hogy a válasz és
     a `/brain` kártya (`node.sources[0]`) vissza tudjon linkelni a hivatalos forráshoz.
   - **Dedup**: a `textSimilar` (Jaccard ≥ 0.82, `BRAIN.md` II.) ne halmozza ugyanazt.
   → `memStore.addMemory` (`doc`/`summary`/`keyword`), `bumpWeight`, `useMemory().addDocument`-mintát követve.

5. **ANSWER — válaszolj a friss web-kontextusból + az agyból, LINKEKKEL.** A frissen behúzott
   forrásokat tedd a system message-be egy **„Web results"** blokként (a meglévő „Relevant earlier
   info" mellé), és a persona (lásd 3. szakasz) utasítja a modellt: **ezekből válaszolj, és tedd oda a
   forrás-linkeket**. Ha sem agy, sem web nem fedi → **mondd ki őszintén**, ne találj ki.
   → `memory.buildSystemMessage` kiegészítése egy „Web results: …" szekcióval (a persona már
     hivatkozik a szekciónevekre — ez a kulcs, hogy a modell megbízzon bennük).

6. **GROW — tanulj a körből (visszacsatolás).** A kör végén:
   `brainChat.observeTurn(userText, assistantText)` → `useBrainLearning().observe(...)` (vocab +
   Markov nő, stage/autonomy emelkedik) + `useMemory().ingest(...)` (kulcsszó-súlyozás, új tények),
   és a 4. lépésben már elmentett web-emlékek. **A következő ugyanilyen kérdésnél a 2. lépés
   (RECALL) megtalálja — nem kell újra keresni.** Ez a „minél többet használják, annál okosabb".

---

## 2. Döntési szabály (mikor keress, mikor ne) — az arbiter kiterjesztése

A `decideRoute` (`arbiter.ts`) ma: `retrieval` → `local-brain` → `local-model` → `fallback`. Told be
egy **`web-search`** utat a `local-model`/`fallback` ELÉ, csak ha az agy lefedettsége gyenge:

```
ha hasRelevantMemory && coverage ≥ 0.6      → 'retrieval'      (az agyból, keresés NÉLKÜL)
különben ha localBrainReady && lefedi       → 'local-brain'    (offline, kulcs nélkül)
különben ha online && coverage < 0.34       → 'web-search'     (ÚJ: keress, tárolj, válaszolj)
különben ha localModelAvailable             → 'local-model'
különben                                     → 'fallback'
```

Adj hozzá a `ArbiterContext`-hez egy `online` jelet (már van: `navigator.onLine`) és egy
`searchAllowed` flaget (alapból ON, kapcsolható — mint a `auri.brain.localAnswer`). A
`brain-bridge/brainChat.ts` `localAnswer`/új `webAnswer` ágban kösd be, **flag mögött, fallbackkel**,
hogy a meglévő chat sose törjön (flag off ⇒ a mai viselkedés változatlan).

---

## 3. Ready-to-paste PERSONA blokk (a system message-be)

Told be a `DEFAULT_SYSTEM`-be (`web/api/chat.ts`) és a `PERSONA`-ba (`web/src/lib/memory.ts`) — a
kettőt **szinkronban** kell tartani (a `BRAIN.md` 7. szakasz szerint). Egy új blokk, a meglévő
„Keep learning" után:

```text
Learn from every message (web-augmented, link-grounded):
- Treat EVERY user message — a question OR a statement — as something to learn from.
- FIRST check your memory ("What you know about the user" / "Relevant earlier info").
  If it already covers the question, answer from it and say which fact/document it came from.
- If memory does NOT cover it, use the "Web results" section provided below: answer FROM
  those results and ALWAYS include the source links. Briefly note you looked it up.
- Never drop the links: every web-grounded claim ends with its source URL.
- What you learn sticks: the new facts, keywords and sources are saved to memory, so next
  time you can answer this from your own brain — without searching again.
- If neither memory nor the web results cover it, say so honestly and offer the best next step.
```

A `buildSystemMessage` a 4. lépésben behúzott forrásokat így fűzze be (a meglévő szekciók után):

```text
Web results (fresh, cite these links):
- <title> — <snippet>  (<url>)
- <title> — <snippet>  (<url>)
```

---

## 4. Implementáció — pontos bekötési pontok (valós fájlok)

| Lépés | Hol | Mit |
|------|-----|-----|
| CAPTURE | `web/src/lib/memStore.ts`, `useMemory.ts` | `addMemory` egy `query` emlékre (forrás=`chat`); a `kind` unió bővítése `'query'`-vel (`memory.ts` + `brain/contracts.ts`), VAGY minimál: csak kulcsszó-mentés a meglévő `ingest`-tel |
| RECALL | `web/src/lib/memory.ts`, `web/src/brain/arbiter.ts`, `answer.ts` | `relevantMemories` + `decideRoute`/`reply`/`recall`; ha lefedi → kész |
| SEARCH | **ÚJ** `web/api/search.ts` | szerveroldali proxy egy keresőhöz (kulcs a szerveren); ad `{title,url,snippet}[]`-et. Kliens-hívás: bővítsd a `web/src/lib/api.ts`-t egy `searchWeb(query)`-vel |
| STORE | `web/src/lib/memStore.ts`, `useMemory.ts` (`addDocument`-minta), `web/src/lib/files.ts` (`chunkText`, `summarizeWithModel`) | `doc` (snippet+URL) + `summary` + `keyword`(+`bumpWeight`); `textSimilar` dedup |
| ANSWER | `web/src/lib/memory.ts` (`buildSystemMessage`) | „Web results" szekció + a persona már „beléjük kapaszkodik" |
| GROW | `web/src/brain-bridge/brainChat.ts` (`observeTurn`), `useMemory.ingest` | minden kör tanít; a web-emlékek perzisztálnak (Supabase belépve / localStorage vendégként, RLS) |
| ROUTE | `web/src/brain/arbiter.ts`, `brain/contracts.ts` | `ArbiterRoute += 'web-search'`; `searchAllowed` flag (`auri.brain.webSearch`, default ON) |
| PERSIST | `web/src/brain/brainStore.ts`, `web/supabase/brain_state.sql` | a gazdagabb snapshot a jsonb-blobban **migráció nélkül** megy (változatlan `BrainPersistState` shape) |

---

## 5. Őszinte határok (kötelező betartani — `BRAIN.md` 19. szakasz szelleme)

- **Web-keresés MA NINCS** a kódban. Ez a prompt vezeti be — kell hozzá a `web/api/search.ts`
  végpont + egy kereső (pl. Brave/Bing/SearXNG/Tavily). Kulcs **csak a szerveren** (mint a chat-proxy).
- **Adatvédelem:** a `query` és a beinjektált memória/web-részletek a modellhez kerülnek (lokális
  Ollaménál a gépen maradnak; Groq/Gemini fallbacknél külső API-hoz mennek). A web-keresés a `query`-t
  a kereső-szolgáltatóhoz küldi — ezt a `/brain` egy sorral jelezze, és legyen kikapcsolható.
- **Forrás-hűség:** a `doc`/`summary` emlékek `source`-a a valódi URL legyen; a válasz **mindig**
  hivatkozzon rá. Soha ne adj ki kitalált linket.
- **Sose törjön a chat:** minden új ág (search/store) `try/catch` + flag mögött, üres/hiba esetén a
  meglévő modell-út fut (a `brainChat.ts` mai mintája).
- **Dedup & budget:** `textSimilar` a halmozódás ellen, `CONTEXT_CHAR_BUDGET` a token-keretért — a
  „Web results" blokk se lépje túl.

---

## 6. Kész, ha

- ☐ Minden bejövő üzenet (kérdés ÉS kijelentés) **rögzül** (CAPTURE) és **megnézi az agyat** (RECALL).
- ☐ Ha az agy nem fedi → **web-keresés linkekkel**, és **minden** találat (link, snippet, kulcsszavak,
  összefoglaló) **eltárolva** `doc`/`summary`/`keyword` emlékként, forrás-URL-lel, dedupelve.
- ☐ A válasz a web-kontextusból jön, **forrás-linkekkel**; ha semmi nem fedi, **őszinte** „nem tudom".
- ☐ A következő ugyanilyen kérdés **az agyból** jön, keresés nélkül (a tanulás visszacsatol).
- ☐ Minden flag mögött, fallbackkel; `npm run typecheck` zöld; a meglévő chat változatlan flag-off-nál.

---

## 7. Mélymagyarázat — miért pont így tanul az agy (a hurok lélektana)

Érdemes megérteni, **miért** ez a helyes felépítés, mert ettől lesz a kód karbantartható és az élmény
hihető. A klasszikus megközelítés az lenne, hogy a modellt „újratanítjuk" minden új információval
(fine-tuning). Ez egy ingyenes, kliensoldali appnál rossz választás: drága (GPU kell), lassú (órák–
napok), nehezen visszavonható (egy tényt nem lehet csak úgy „kiszedni" a súlyokból), és nem
felhasználónként izolált. Helyette a BRAIN **memóriát + kontextus-injektálást** használ (`BRAIN.md`
I–II. rész), és ehhez teszünk hozzá egy **web-augmentált tanuló hurkot**. A modell változatlan marad;
ami nő, az a **kontextus**, amit a kérdés elé teszünk — és most már nemcsak a beszélgetésből és a
feltöltött fájlokból, hanem a **netről behúzott, lokálisan eltárolt tudásból** is.

A hurok lényege a **visszacsatolás összeszorzódása**. Az első alkalommal egy ismeretlen kérdés a
3. lépésben (SEARCH) web-keresést indít, ami lassabb és külső szolgáltatótól függ. De ekkor a
4. lépés (STORE) **véglegesen lehorgonyozza** a tudást a memóriában `doc`/`summary`/`keyword`
emlékként, a forrás-URL-lel együtt. Másodszorra ugyanaz a kérdés már a 2. lépésben (RECALL) megáll: a
`relevantMemories` a `doc`/`summary` +3 bónusza miatt előrehúzza a korábban behúzott forrást, a
`decideRoute` `'retrieval'`-t ad, és **keresés nélkül, azonnal, offline-közeli sebességgel** válaszol.
Vagyis minden web-keresés egy **egyszeri befektetés**, ami a jövőben kamatozik: minél többet
használják, annál ritkábban kell ténylegesen keresni, és annál többször jön a válasz a saját agyból.
Ez a „minél többet használják, annál okosabb" matematikai magja — nem marketing, hanem a tár+retrieval
természetes következménye.

A második kulcsgondolat a **tudás-rés (gap) mint hajtóerő**. A CAPTURE lépés azért menti el a nyers
kérdést is, nem csak a választ, mert a **meg nem válaszolt kérdés a legértékesebb jelzés**: pontosan
megmondja, hol „lyukas" az agy. Egy hagyományos asszisztens elfelejti, mit nem tudott; ez az agy
**megjegyzi a saját hiányosságait**, és ezekből épít prioritási listát a kitöltéshez (10. szakasz). Így
a tanulás nem véletlenszerű, hanem **a valódi használat által vezérelt**: azokat a témákat mélyíti,
amelyeket tényleg kérdeznek, nem amelyeket mi előre kitalálunk. Ez teszi a `/brain` oldalon látható
növekedést **a felhasználó tükörképévé** — az agy alakja idővel a felhasználó érdeklődését rajzolja ki.

A harmadik elv az **őszinte rétegzettség**. Háromféle tudás él egymás mellett, csökkenő bizonyossággal:
(a) a felhasználó saját kijelentései és feltöltött dokumentumai (`fact`/`doc`, a legmegbízhatóbb,
ezért a persona ezeket sorolja előre); (b) a netről behúzott, forrással hitelesített tudás
(`doc`/`summary` web-URL-lel); (c) a literal-agy statisztikai megfogalmazása (Markov/Q→A, a leggyengébb,
csak végszükségben). A `answer.composeLocalAnswer` már pontosan ebben a prioritásban dolgozik — a
web-réteg ennek a (b) szintjére illeszkedik be, a személyes (a) alá, a statisztikai (c) fölé. Ettől a
válasz **mindig a lehető legmegbízhatóbb forrásból** jön, és sosem ad ki nyers „babble"-t tudás helyett.

---

## 8. Új funkció — Forrás-bizalom és frissesség (trust + freshness)

Nem minden forrás egyenértékű, és nem minden tudás marad sokáig igaz. Vezess be két új mezőt a
web-eredetű emlékekhez (a meglévő `Memory` shape `weight`/`source` mellé, vagy a `prefs`/`meta`
JSON-be, hogy ne kelljen sémát törni):

- **`trust` (0..1) — forrás-bizalom.** Számítsd a domainből: hivatalos doksi (developer.mozilla.org,
  nodejs.org, react.dev, a `seed/sources.ts` regisztere) → magas; ismert tech-oldal → közepes;
  ismeretlen blog → alacsony. A `relevantMemories` pontszámához add hozzá `trust * 4`-et, így a
  megbízhatóbb forrás hamarabb kerül kontextusba. Több azonos állítást **különböző** domainekről
  → bizalom-növelés (konszenzus).
- **`fetchedAt` + `ttlDays` — frissesség.** A web-emlékek **avulnak**: egy verziófüggő API vagy ár
  pár hónap alatt elavul. Ha egy `doc`/`summary` emlék `fetchedAt + ttlDays` lejárt ÉS most kérdezik,
  a `decideRoute` adjon `'web-search'`-t a `'retrieval'` helyett (**re-fetch**), majd a STORE
  **frissítse** a régi emléket (ne duplikálja — `textSimilar` + azonos `source` → update). A `ttlDays`
  témafüggő: hír/ár → rövid (1–7 nap), stabil fogalom („mi az a HTTP") → hosszú (180+ nap).

Ez adja a „mindig friss, mégis offline-gyors" egyensúlyt: a stabil tudás bent marad az agyban, a
romlandó pedig magától megújul, amikor releváns. A `/brain` kártya egy apró „🕒 frissítve N napja"
jelzéssel mutathatja a forrás korát (a `BrainStats.lastLearnedAt` mintájára).

---

## 9. Új funkció — Kérdés-kiterjesztés és újrarangsorolás (query expansion + re-rank)

A keresés minősége azon áll vagy bukik, hogy **mire** keresünk. Egy nyers felhasználói mondat gyakran
rossz keresőkifejezés. Told be a SEARCH elé egy könnyű **query-expander** lépést (tisztán a meglévő
`extractKeywords` + `detectLang` segítségével, modell nélkül is működik):

1. **Kulcsszavasítás:** a `extractKeywords(query, 8)` adja a mag-kifejezést (a stopszavak nélkül),
   így „Hogyan tudnék egy reszponzív menüt csinálni?" → `reszponzív menü css`.
2. **Nyelv-páros keresés:** `detectLang` szerint keress a felhasználó nyelvén **és** angolul is, majd
   olvaszd össze a találatokat — a műszaki tartalom java angolul pontosabb, de a magyar nyelvű
   forrás közelebb áll a kérdéshez. Dedup domain szerint.
3. **2–3 variáns:** generálj néhány átfogalmazást (szinonimák, „example", „docs", „how to") és a
   top találatokat **egyesítsd**, ne csak az elsőt vedd.

Keresés után **újrarangsorolás (re-rank)**, mielőtt tárolnál: minden találati `snippet`-re számold a
`extractKeywords(snippet)` és a kérdés kulcsszavainak átfedését (a `relevantMemories` +5/egyezés
logikájával), szorozd a `trust`-tal, és csak a **top 3–6**-ot tárold (4. lépés). Így nem szemeteled
tele a memóriát gyenge találatokkal, és a `CONTEXT_CHAR_BUDGET` keret is tartható marad. Ez a lépés a
„retrieval minősége" — a `BRAIN.md` 16. szakasz „okosabb visszakeresés" irányának olcsó, azonnali
változata, vektor-beágyazás nélkül.

---

## 10. Új funkció — Tudás-rések és kíváncsisági hurok (gaps + curiosity)

A CAPTURE lépésben elmentett, **meg nem válaszolt** kérdések alkossanak egy külön **gap-listát** (egy
`kind:'query'` emlék `answered:false` jelzővel, vagy egy `auri.brain.gaps` kulcs). Ez két dolgot ad:

- **Proaktív kitöltés (háttér):** amikor az app tétlen (a felhasználó nem gépel), egy **debounce-olt,
  ráta-limitált** háttérfeladat kiveszi a legtöbbször előforduló kitöltetlen gap-et, lefuttatja rá a
  SEARCH+STORE-t, és **előre feltölti** az agyat — így mire a felhasználó újra kérdez róla, már kész a
  válasz. (Szigorúan flag mögött, hogy ne fogyasszon kvótát akarata ellenére.)
- **„Ezt is megtanultam" visszajelzés:** a `/brain` mutathat egy kis „nemrég kitöltött rés" listát
  (a `recentWords()` mintájára), így a felhasználó **látja az agyat tanulni** — pont az a vizuális
  „okosodás", amit a `BRAIN.md` 16. szakasz kér.

A gap-lista egyúttal **prioritási jel** a 9. szakasz query-expanderének: a gyakran visszatérő,
megválaszolatlan témákra érdemes több variánssal, mélyebben keresni. A kíváncsisági hurok teszi az
agyat **a passzív tárból aktív tanulóvá** — nemcsak reagál, hanem a saját hiányosságait is gyűjti és
tölti.

---

## 11. Új funkció — Visszajelzés-alapú megerősítés (feedback / 👍 👎)

A tanulás akkor lesz igazán önjavító, ha a **felhasználó visszajelzése** is súlyt módosít. Tegyél a
chat-válaszok alá egy apró 👍/👎-t (vagy használd a meglévő javítás-érzékelést a personából):

- **👍** → a választ tápláló emlékek (`relevantMemories` által kiválasztott `doc`/`fact`/`summary`)
  `bumpWeight`-et kapnak, és a forrásuk `trust`-ja kicsit nő → legközelebb előbb kerülnek elő.
- **👎 vagy javítás** („nem, valójában X") → az érintett emlék `weight`-je csökken, vagy
  `deleteMemory`/felülírás; a forrás `trust`-ja csökken. A persona már ma „azonnal elfogadja a
  javítást" — ez most **tartósan** is rögzül a súlyokban, nemcsak az adott körre.
- **Auto-pin a megerősített tudásra:** ha egy tényt többször is 👍-öztek vagy ismételten megerősítettek,
  `setMemoryPinned(true)` → szinte mindig bekerül a kontextusba (`relevantMemories` +100).

Ez egy **könnyű megerősítéses jel** (nem RL a szó szigorú értelmében, csak súly-hangolás), de pont
elég ahhoz, hogy az agy a *jó* forrásokat erősítse és a *rosszakat* elhalványítsa — emberi felügyelet
mellett, visszavonhatóan, a Memória-nézetből bármikor felülbírálva.

---

## 12. Új funkció — Idézetek és visszakövethetőség a UI-ban (citations)

A „linkekkel" követelmény nemcsak a tárolásról szól, hanem a **megjelenítésről** is. Tedd a válaszban
és a `/brain`-en visszakövethetővé a forrást:

- **Inline idézet-jelek:** a web-grounded válasz mondatai kapjanak `[1]`, `[2]` jelölést, alul egy
  **„Források"** listával (`[1] <cím> — <url>`). A `buildSystemMessage` „Web results" blokkja már
  sorszámozva adja át, a persona pedig utasítja a modellt, hogy ezekre a számokra hivatkozzon.
- **Forrás-chipek a chatben:** a válasz alatt kattintható chip-ek (cím + domain-favicon), új lapra
  nyílnak. Ez a meglévő `node.sources[0]` → „↗ official docs · host" mintát viszi a chat-felületre is.
- **A `/brain`-en már létezik** a forrás-link a csomópont-kártyán (AI-2 megcsinálta) — a web-doc
  node-ok `sources[0]`-ja a valódi URL, így a 3D agyban **vizuálisan visszakövethető**, honnan tudja
  az agy, amit tud. Egy „csak forrással hitelesített tudás" szűrő (kapcsoló) megmutathatja, mennyi az
  agyból valóban lehorgonyzott vs. statisztikai.

A visszakövethetőség **bizalmat ad** (a felhasználó ellenőrizheti a forrást) és **őszinte** marad (a
kitalált link tilalma a 5. szakaszból itt válik láthatóvá): ha nincs forrás, nincs idézet-jel sem.

---

## 13. Új funkció — Gyorsítótár, ráta-limit és költségkeret (cache + budget)

A web-keresés a hurok egyetlen **külső, fizetős/limitált** lépése — kezeld tudatosan:

- **Keresés-cache:** mielőtt a SEARCH-öt elindítod, nézd meg, kerestél-e már nemrég ugyanerre
  (normalizált query-kulcs → `auri.brain.searchCache`, rövid TTL). Találat → a tárolt eredményt
  használd, ne hívd újra a keresőt. Ez gyors **és** kvótát spórol.
- **Ráta-limit:** percenként/óránként maximált keresés-szám; túllépéskor a `decideRoute` essen vissza
  `'local-model'`/`'fallback'`-re és válaszoljon a meglévő agyból, amennyire tud (graceful degradation).
- **Token/karakter-keret:** a „Web results" blokk tartsa a `CONTEXT_CHAR_BUDGET`-et — inkább kevesebb,
  jobb forrás, mint sok zaj. A snippeteket vágd a 9. szakasz re-rank top-N-jére.
- **Batch a gap-kitöltéshez:** a 10. szakasz háttérfeladata több gap-et **egy** keresési ablakban,
  ritkán fusson, sose a felhasználó aktív gépelése közben.

Így a rendszer a free-tier valóságban is megáll (mint a `api/chat.ts` provider-lánca), és sosem
„ég el" a kvóta egy ismétlődő kérdésen.

---

## 14. Új funkció — Adatvédelem és tartalom-szűrés (privacy + safety)

A web-keresés a `query`-t **kiküldi egy külső kereső-szolgáltatóhoz** — ez új adatvédelmi felület,
kezeld őszintén (a `BRAIN.md` 14. szakasz szellemében):

- **PII-redakció keresés előtt:** mielőtt a query-t a kereshez küldöd, szűrd ki a nyilvánvaló
  személyes adatokat (e-mail, telefonszám, a profil neve), vagy keress csak a **kulcsszó-magra**
  (9.1), ne a teljes nyers mondatra. A személyes réteg (`fact`/profil) **soha** nem megy a kereshez.
- **Kapcsoló + jelzés:** a web-keresés legyen ki/bekapcsolható (`auri.brain.webSearch`), és a UI
  jelezze, amikor ténylegesen keres („🌐 utánanézek…"), hogy a felhasználó tudja, mi hagyja el a gépét.
  Lokális Ollama mellett a chat a gépen marad; a keresés viszont mindig külső — ezt külön mondd ki.
- **Tartalom-szűrés a behúzott oldalon:** a `snippet`/letöltött szöveg mehet át egy egyszerű
  szűrőn (script/HTML-tisztítás már kell a kinyeréshez; tedd hozzá a nyilván káros/spam tartalom
  eldobását), hogy ne tárolj el szemetet vagy veszélyes utasítást a memóriába (prompt-injection
  védelem: a behúzott web-szöveget **adatként** kezeld, ne utasításként — a persona ezt mondja ki).
- **Felhasználói kontroll:** a web-eredetű emlékek a Memória-nézetben ugyanúgy törölhetők/exportálhatók,
  és egy „web-tudás törlése" gomb egyben kiüríti az összes `source`-URL-es emléket.

---

## 15. Új funkció — Entitás-összevonás és tudás-konszolidáció (merge/consolidate)

Ahogy nő az agy, a legnagyobb veszély a **halmozódás** (ugyanaz az állítás tízszer, kicsit másképp). A
`textSimilar` dedup (4. lépés) az első védvonal, de tegyél mellé egy időnkénti **konszolidációt**:

- **Near-duplicate merge:** a `textSimilar` (Jaccard ≥ 0.82) klasztereket von össze egyetlen,
  legmagasabb `trust`/`weight`-ű emlékké, a forrás-URL-eket egy `sources[]`-be gyűjtve (több forrás =
  erősebb bizalom). Kevesebb, jobb emlék → gyorsabb `relevantMemories`, tisztább kontextus.
- **Periodikus tömörítés:** hosszú, sok `doc`-chunkos témákat időnként egyetlen `summary`-vé sűríts
  (a `files.ts` `summarizeWithModel` mintájára), és a nyers chunkokat archiváld/ritkítsd. Így a lényeg
  megmarad token-keret alatt (`BRAIN.md` 16. „auto-összefoglaló" iránya).
- **Megerősített tény → magasabb réteg:** ha egy tényt több forrás **és** felhasználói 👍 is megerősít,
  emeld stabil, `pinned`-közeli rétegbe — ez lesz az agy „biztos tudása", amit szinte mindig használ.

A konszolidáció a `BrainStats.fullnessPct` lassú, **egészséges** növekedését biztosítja: nem a
szemét-emlékek számától telik meg, hanem a valódi, összevont tudástól — és a `/brain` 3D térképe így
**sűrű, de rendezett** agyat mutat, nem zajfelhőt.

---

## 16. Megfigyelhetőség — mérd, hogyan nő az agy (metrics)

Amit nem mérsz, azt nem tudod javítani. Vezess pár olcsó számlálót (a `BrainStats`-hoz/`brain_state`-hez):

- **Hit-rate:** a kérdések hány %-át fedte az agy keresés nélkül (RECALL-hit) vs. mennyi indított
  web-keresést. Ahogy nő az agy, a hit-rate-nek **emelkednie** kell — ez a tanulás közvetlen mérőszáma.
- **Keresés/nap, gap-szám, friss vs. avult emlékek aránya, átlag `trust`.** Egy mini „agy-egészség"
  panel a `/brain`-en ezeket mutathatja.
- **Növekedés:** vocab, `doc`/`summary`/`keyword`-szám, `lastLearnedAt` — a `BrainStats` már szállítja,
  csak ki kell egészíteni a web-eredetű darabok bontásával.

Ezek nemcsak fejlesztői eszközök: a felhasználónak is **bizonyítják**, hogy az agy tényleg okosodik —
a hit-rate emelkedő görbéje a leghihetőbb „minél többet használod, annál jobb" jelzés.

---

## 17. Lépcsős bevezetés (rollout) — milyen sorrendben építsd

Ne egyszerre. Minden lépés önmagában is működő, flag mögött:

1. **MVP:** `api/search.ts` + `searchWeb()` (api.ts) + a 1–6. hurok (CAPTURE→GROW), `doc`/`summary`/
   `keyword` tárolással és a „Web results" persona-blokkal. Ennyitől már **él** a web-augmentált tanulás.
2. **Minőség:** 8. (trust+freshness) és 9. (query-expansion+re-rank) — a keresés pontossága ugrik.
3. **Önjavítás:** 10. (gaps/curiosity) és 11. (feedback) — az agy a használatból irányítottan mélyül.
4. **Élmény + bizalom:** 12. (idézetek) és 16. (metrics) — láthatóvá és ellenőrizhetővé válik a tudás.
5. **Skála + biztonság:** 13. (cache/limit), 14. (privacy/safety), 15. (konszolidáció) — éles, sok
   felhasználós használatra.

Minden lépésnél tartsd a 5. szakasz őszinte határait és a `BRAIN_BUILD.md` zóna-szabályait: a tanuló
motor `web/src/brain/**`, a perzisztencia `brainStore.ts`/`brain_state.sql`, a közös fájlokat (App.tsx,
main.tsx, persona) csak a kijelölt integrációs ponton, flag mögött, fallbackkel. Így az agy **töretlen
chat mellett**, fokozatosan, mérhetően és visszavonhatóan nő — pontosan annyit, amennyit használják.
