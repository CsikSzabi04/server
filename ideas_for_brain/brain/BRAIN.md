# AuriGPT — A BRAIN: hogyan működik, hogyan tanul, hogyan „okosodik"

> Ez a dokumentum egyszerre **magyarázat** és **prompt**: elmagyarázza az Auri-asszisztens
> „agyának" (BRAIN) működését a *tényleges kódunk* alapján, és úgy van megírva, hogy ha
> odaadod egy embernek vagy egy másik AI-nak, pontosan értse, mi történik a motorháztető alatt,
> mit jelent itt a „tanulás", és hol vannak a valós határok. Cél: lenyűgöző élmény **és** őszinte,
> reális kép — semmi varázslat, csak jól megépített memória + kontextus.

---

## 0. Hogyan olvasd ezt

A BRAIN nem egy különálló program, hanem egy **réteg** az AuriGPT köré, amely három dolgot csinál
folyamatosan: (1) **megfigyeli** a beszélgetést és a feltöltött fájlokat, (2) **eltárol** belőlük
tényeket, kulcsszavakat, dokumentum-részleteket és egy felhasználói profilt, majd (3) **minden új
kérdéshez hozzácsatolja a releváns emlékeket** a modellnek küldött utasításhoz. Ettől tűnik úgy,
mintha Auri „emlékezne rád" és „egyre jobban ismerne" — pedig a háttérben nincs misztikum, csak egy
gondosan felépített memória- és kontextus-rendszer.

A dokumentum végigveszi a teljes láncot: az adatfolyamot egy üzenet életében, a memória-motort,
a kontextus-injektálást, a personát, a tárolást, a dokumentum-feldolgozást, a vizualizációt, a
teljesítményt, az adatvédelmet és a jövőbeli irányokat. A szakaszok önállóan is olvashatók.

---

## 1. A nagy kép — mi az Auri „agya"?

Képzeld el Aurit úgy, mint egy nagyon gyors asszisztenst, akinek van egy **jegyzetfüzete rólad**.
Ahányszor beszélgettek, Auri felír a füzetbe pár fontos dolgot: a nevedet, hogy milyen nyelven
beszélsz, mik a visszatérő témáid, milyen tényeket osztottál meg magadról, és mit tartalmaznak a
feltöltött dokumentumaid. A következő kérdésnél Auri **gyorsan átfutja a füzetet**, kikeresi azt a
néhány bejegyzést, ami a mostani kérdéshez tartozik, és **odateszi a szeme elé**, mielőtt válaszol.
Így a válasz nem általános, hanem **rád szabott**: a saját korábbi infóidra és dokumentumaidra épül.

Ez a „jegyzetfüzet + odateszem a szeme elé" mechanizmus a BRAIN lényege. Technikailag két nagy
darabból áll:

- **Memória (a jegyzetfüzet):** tartós tároló a tényeknek, kulcsszavaknak, dokumentum-részleteknek
  és a profilodnak. Belépve a felhőben (Supabase), vendégként a böngésződben (localStorage).
- **Kontextus-injektálás (a szem elé tevés):** minden kérés előtt összeállítjuk a personát + a
  legrelevánsabb emlékeket egyetlen *rendszerüzenetbe*, és ezt küldjük a modellnek a kérdéseddel
  együtt.

A modell (a tényleges „nyelvi agy", pl. a lokális Ollama, vagy fallbackként a Groq/Gemini) **nem
változik** — minden látogatónál ugyanaz a modell fut. Ami **változik**, az a kontextus, amit a
modell elé teszünk: a te memóriád. Ezért lesz Auri *neked* okosabb, anélkül, hogy a modellt magát
újra kellene tanítani.

---

## 2. Az őszinte keret: mit jelent itt a „tanulás"?

Ezt fontos tisztán látni, mert ettől lesz az elvárás reális. Amikor azt mondjuk, hogy Auri „tanul"
és „okosodik", **nem** arról van szó, hogy a mesterséges intelligencia modell súlyait átképezzük
(ez a *fine-tuning*, ami drága, lassú, és külön infrastruktúrát igényel). Helyette **memóriát +
kontextus-injektálást** használunk — ezt a szakmában gyakran „RAG"-szerű (retrieval-augmented
generation) megközelítésnek hívják kicsiben.

A különbség a gyakorlatban viszont alig érződik: mivel minden válasz előtt Auri **látja a rólad
felhalmozott tudást**, úgy viselkedik, mintha emlékezne rád és tanult volna belőled. A neveden
szólít, a korábbi témáidra utal, a feltöltött dokumentumaidból idéz. A felhasználó számára ez
pontosan „okosodás" — csak a megvalósítás más, mint a fine-tuning.

Miért ez a jó döntés egy ingyenes, kliensoldali appnál?

- **Azonnali:** egy új tény azonnal hat a következő válaszra — nincs órákig tartó újratanítás.
- **Visszavonható és szerkeszthető:** bármelyik emléket törölheted, rögzítheted vagy átírhatod a
  Memória-nézetben. Egy fine-tuned modellből nem lehet egy tényt csak úgy „kiszedni".
- **Adatvédő:** a tudás a *te* fiókodhoz/böngésződhöz tartozik, nem ég bele egy mindenki által
  használt modellbe.
- **Olcsó:** nem kell GPU-s tanítás; csak szöveget tárolunk és válogatunk.

A határ szintén őszinte: a BRAIN annyira „okos", amennyire jó (a) amit eltárol, és (b) amit a
kérdéshez ki tud választani. Ezért fektettünk hangsúlyt a kinyerésre, a relevancia-pontozásra és a
personára, amely megmondja a modellnek, hogyan **használja** ezt a kontextust.

---

## 3. Az architektúra madártávlatból

A BRAIN néhány, jól elkülönülő fájlból áll a `web/` frontendben. Mindegyiknek egy felelőssége van:

- **`src/lib/memory.ts` — a motor (tiszta logika).** Itt él a `PERSONA`, a kulcsszó-kinyerés
  (`extractKeywords`), a név-felismerés (`detectName`), a nyelv-felismerés (`detectLanguage`), a
  tény-kinyerés, a `analyzeTurn` (egy beszélgetési kör elemzése), a `relevantMemories`
  (relevancia-válogatás) és a `buildSystemMessage` (a végső rendszerüzenet összeállítása). Ez a
  fájl szándékosan **böngésző- és szerverfüggetlen**: nem tud arról, hol tárolunk — csak elemez és
  szöveget épít.

- **`src/lib/memStore.ts` — a tároló.** Ez dönti el, hova kerülnek az adatok: **belépve a
  Supabase**-be (a `profiles` és `memories` táblákba, soronkénti jogosultság-szabályozással), **vendégként
  a `localStorage`**-ba. Egyetlen egységes felület (`getProfile`, `saveProfile`, `listMemories`,
  `addMemory`, `bumpWeight`, `setMemoryPinned`, `deleteMemory`, `clearAll`, `exportAll`,
  `importAll`), amely `userId | null` paramétert kap, és magától a megfelelő háttértárat használja.

- **`src/hooks/useMemory.ts` — a React-ragasztó.** Betölti a profilt és az emlékeket a bejelentkezett
  felhasználó (vagy a vendég) szerint, és kiad két kulcsfontosságú függvényt az appnak:
  `systemMessage(query)` (a kontextus-injektáláshoz) és `ingest(userText, assistantText)` (a
  tanuláshoz minden kör után). Plusz a kezelő-műveletek: `addDocument`, `removeDoc`,
  `updateProfile`, `pinMemory`, `removeMemory`, `clearAll`, `exportData`, `importData`.

- **`src/lib/files.ts` — a dokumentum-feldolgozó.** Beolvassa a feltöltött szövegfájlokat
  (`readDocument`), darabokra bontja (`chunkText`), és best-effort módon összefoglaltatja a
  modellel (`summarizeWithModel`).

- **`src/lib/chatStore.ts` — a beszélgetés-tár.** A teljes előzményt (beszélgetések + üzenetek)
  tárolja és tölti, szintén Supabase + localStorage kettősséggel. Ez adja az ARCHÍVUM oldalsávot
  és az „Új chat" funkciót.

- **A vizualizáció:** `src/components/BrainCard.tsx` (a 3D mag fölé húzva felugró élő „BRAIN"
  kártya) és `src/components/MemoryView.tsx` (a teljes Memória-nézet: profil-szerkesztés, tények,
  dokumentumok, kulcsszavak, export/import/törlés).

- **A bekötés:** `src/App.tsx` köti össze a darabokat — itt épül a kérés (a `systemMessage` által),
  itt indul a streamelés a modell felé, és itt fut le a tanulás (`ingest`) minden válasz után.

- **A séma:** `supabase/schema.sql` hozza létre a `conversations`, `messages`, `profiles`,
  `memories` táblákat soronkénti jogosultság-szabályozással (Row Level Security), hogy mindenki
  **kizárólag a sajátját** lássa.

A rétegek tudatosan szét vannak választva: a *motor* nem tud a *tárolásról*, a *tárolás* nem tud a
*UI-ról*. Így ha holnap lecserélnénk a Supabase-t valami másra, csak a `memStore.ts`-t kellene
átírni; ha okosabb kinyerést akarnánk, csak a `memory.ts`-t.

---

## 4. Egy üzenet teljes útja (end-to-end)

A legjobban úgy érted meg a BRAIN-t, ha követed, mi történik, amikor beírsz egy üzenetet és
megnyomod a küldést. A lépések (a tényleges `App.tsx` `send` függvénye alapján):

1. **Begépeled a kérdést, és küldöd.** Az app azonnal megjeleníti az üzeneted, és „thinking"
   állapotba kapcsol (a 3D mag is reagál).

2. **A BRAIN összerakja a rendszerüzenetet.** Meghívjuk a `memory.systemMessage(text)`-et, ami a
   `buildSystemMessage`-en keresztül összefűzi: a **personát** (ki Auri, hogyan használja a
   memóriát), majd a **profilodat** ("What you know about the user: …"), végül a **kérdéshez
   legrelevánsabb emlékeket** ("Relevant earlier info: …"). Ez egyetlen `system` szerepű üzenet.

3. **Összeáll a teljes üzenetlista.** A rendszerüzenet kerül legelőre, utána a beszélgetés eddigi
   menete + az új kérdésed. Ezt küldjük a modellnek (`streamChat`).

4. **A kérés a provider-láncon megy.** A Vercel-proxy (vagy dev-proxy) eldönti, ki válaszoljon:
   **lokális Ollama** (ha a géped megy és elérhető), különben **Groq**, különben **Gemini**. A
   modell a rendszerüzenetben **látja a memóriádat**, ezért személyre szabottan válaszol.

5. **A válasz tokenenként streamel vissza.** A szöveg élőben gépelődik a panelbe (és ha be van
   kapcsolva a hang, fel is olvasódik mondatonként).

6. **Mentés.** A kérdésedet és Auri válaszát elmentjük a beszélgetéshez (Supabase belépve, lokál
   vendégként), így az ARCHÍVUM-ban később visszatölthető.

7. **Tanulás (`ingest`).** A válasz végén lefut a `memory.ingest(userText, assistantText)`: kinyeri
   a kulcsszavakat, felismeri, ha bemutatkoztál (név), érzékeli a nyelvet, és elment minden új,
   tartós tényt. **Ettől a kör után Auri már egy kicsivel többet tud rólad** — a következő kérdésnél
   ez a friss tudás is bekerülhet a kontextusba.

A 7. lépés a „tanulás" pillanata; a 2. lépés a „felhasználás" pillanata. A kettő együtt adja a
visszacsatolást, amitől a rendszer **körről körre jobban illeszkedik hozzád**.

---

## 5. A memória-motor (`memory.ts`) részletesen

Ez a fájl a BRAIN „elemző agya". Nincs benne hálózat, nincs benne UI — csak szöveget kap, és
strukturált tudást ad vissza. Nézzük a részeit.

### 5.1 Kulcsszó-kinyerés (`extractKeywords`) + stopszavak + gyorsítótár

A kulcsszavak adják a témákat, amik alapján később megtaláljuk a releváns emlékeket. A működés:

- A szöveget kisbetűsítjük, és kiszedjük belőle a legalább 3 betűs/számjegyű „szavakat" egy
  **Unicode-tudatos** mintával (`\p{L}\p{N}`), hogy a magyar ékezetes szavak is helyesen
  szerepeljenek.
- Kiszűrjük a **stopszavakat** — a gyakori, jelentés nélküli kötőszavakat, névmásokat stb. — egy
  beépített magyar + angol listával (pl. „a, az, és, hogy, nem, the, and, is, to…"). Ezek csak zajt
  adnának.
- A maradékot **gyakoriság szerint** rangsoroljuk, és a top N-et adjuk vissza (alapból 10).

Mivel ezt a függvényt minden válogatáskor minden emlékre lefuttatjuk, **gyorsítótárazzuk** az
eredményt a bemenet alapján (`kwCache`). Így egy emlék kulcsszavait egyszer számoljuk ki, utána
újrahasználjuk — ettől marad gyors a rendszer akkor is, ha több ezer emléked van. A cache korlátos
(ha túl nagyra nő, kiürül), hogy ne fogyassza a memóriát.

> Megjegyzés: ez egy **egyszerű, nyelvfüggetlen** kulcsszó-kinyerés, ami szerver és AI nélkül is
> működik. Nem tökéletes (nem ismer fel szinonimákat vagy ragozási töveket), de gyors, ingyenes és
> meglepően jól elég a relevancia-jelzéshez. A jövőbeli irányoknál látjuk, hogyan lehetne okosabb.

### 5.2 Név-felismerés (`detectName`)

Ha bemutatkozol, Auri **megjegyzi a neved**, és onnantól a neveden szólít. A felismerés néhány
mintára épül: „a nevem X", „hívj X-nek", „X vagyok", illetve angolul „my name is X", „I'm X",
„call me X". A talált nevet egy kis tiltólistával szűrjük (pl. „fáradt vagyok" → ne legyen „Fáradt"
a neved). Ez egy **heurisztika**, nem tökéletes — ezért a Memória-nézetben bármikor kézzel
javíthatod a nevet.

### 5.3 Nyelv-felismerés (`detectLanguage`)

Csak **erős jelnél** állítunk be nyelvet: ha ékezetes magyar karaktereket lát (á, é, í, ó, ö, ő, ú,
ü, ű), „Hungarian"-t jelöl. Szándékosan óvatos — inkább nem tippel, mint hogy tévedjen. A persona
amúgy is utasítja a modellt, hogy a felhasználó nyelvén válaszoljon, így ez csak egy plusz jel a
profilban.

### 5.4 Tény-kinyerés (`extractFacts`)

A rövid, **kijelentő, első személyű** mondatokat tényként mentjük (pl. „Imádom a focit", „A
projektem a CliMarkAI", „I work as a developer"). A szűrés: ne legyen kérdés (`?`-re végződő), ne
legyen túl hosszú (max ~200 karakter), és tartalmazzon első személyű jelzőt (én, nekem, szeretem,
projekt, vagyok, I'm, my, i like…). Így a beszélgetésből a **rólad szóló, tartós információk**
kerülnek a memóriába, nem a kérdéseid vagy a csevegés zaja.

### 5.5 `analyzeTurn` — egy kör elemzése

A `analyzeTurn(userText, assistantText)` fogja össze a fentieket: visszaad egy objektumot a
kör **kulcsszavaival** (a kérdésből és a válaszból együtt), az esetleg felismert **névvel**, a
**nyelvvel** és a kinyert **tényekkel**. Ezt használja a `useMemory.ingest`, hogy frissítse a
memóriát minden válasz után.

---

## 6. A kontextus-injektálás (`buildSystemMessage` + `relevantMemories`)

Ez a BRAIN „felhasználó agya": eldönti, **mit lát a modell** a kérdésed előtt. A cél, hogy a
*legrelevánsabb* tudás kerüljön be — tömören, hogy ne pazaroljunk tokent, de elég ahhoz, hogy a
válasz személyre szabott legyen.

### 6.1 Relevancia-pontozás (`relevantMemories`)

Minden emlék kap egy pontszámot a mostani kérdéshez képest:

- **Rögzített emlék (pinned): +100.** Amit te fontosnak jelöltél, az szinte mindig bekerül.
- **Súly (weight):** a gyakrabban előforduló / megerősített emlékek erősebbek (a kulcsszavak súlya
  nő, ahányszor előjönnek).
- **Kulcsszó-átfedés: +5** minden olyan szóra, ami a kérdésben ÉS az emlékben is szerepel. Ez a fő
  relevancia-jel: a kérdéshez témailag kapcsolódó emlékek emelkednek ki.
- **Dokumentum/összefoglaló bónusz: +3.** A feltöltött fájljaidból származó `doc`/`summary`
  emlékek **megbízható kontextusként** előnyt kapnak, hogy hamarabb bekerüljenek a válogatásba —
  pont ezért tudsz a saját dokumentumaidból pontosabb választ kapni.

A pontszám szerint rendezünk, és a **top 8** emléket választjuk ki (a 0 pontosakat eldobjuk). Ez a
„top 8" tudatos kompromisszum: elég ahhoz, hogy gazdag legyen a kontextus, de nem annyi, hogy
tokenben elszálljon (ami a free-tier API-knál — Groq/Gemini — fontos).

### 6.2 A rendszerüzenet szerkezete (`buildSystemMessage`)

A végső `system` üzenet három blokkból áll, ebben a sorrendben:

1. **PERSONA** — ki Auri, és hogyan kezelje a memóriát (lásd a 7. szakaszt).
2. **„What you know about the user: …"** — a profilod tömör összefoglalója: név, becenév, nyelv,
   hangnem, érdeklődés, „rólam" jegyzet (amik ki vannak töltve).
3. **„Relevant earlier info: …"** — a kérdéshez legrelevánsabb tények / dokumentum-részletek /
   összefoglalók, felsorolásként.

Plusz, ha tudjuk a nevedet, hozzáfűzünk egy sort: „When natural, address the user by name (…)."

Kulcsfontosságú részlet: a persona **pontosan ezekre a szekciónevekre hivatkozik** („What you know
about the user", „Relevant earlier info"). Így a modell tudja, hogy ezek **valódi, megbízható
adatok rólad** a hosszú távú memóriából — nem általános tudás, hanem a te kontextusod. Ettől
„kapaszkodik bele" a modell a saját adataidba.

---

## 7. A persona — az utasítás-réteg

A persona (a `PERSONA` konstans a `memory.ts`-ben, és a vele azonos `DEFAULT_SYSTEM` a proxy
`api/chat.ts`-ében a konzisztenciáért) az a szöveg, amely **megmondja a modellnek, hogyan
viselkedjen és hogyan használja a memóriát**. A lényege:

- **Válaszadás:** a felhasználó nyelvén, alapból angolul; tömören, de sosem annyira, hogy a válasz
  hibás vagy használhatatlan legyen — „helyesség előbb, rövidség utána". Olvassa ki a kérdés
  szándékát, és a leghasznosabb, legközvetlenebb választ adja.
- **A memória használata (ettől okos):** a „What you know about the user" és „Relevant earlier
  info" blokkok **valódi tények és dokumentum-részletek** róla; bízzon bennük és aktívan használja
  őket. A felhasználó saját dokumentumait és kijelentéseit **előbbre sorolja** az általános
  tudásnál; ha ütköznek, a dokumentumot/tényt kövesse, és röviden jelezze.
- **Dokumentum-kérdéseknél:** a megadott részletekből válaszoljon; ha a részlet nem tartalmazza a
  választ, mondja meg, mi hiányzik — **ne találja ki**.
- **Folyamatos tanulás:** vegye észre az új, tartós tényeket, neveket, célokat, preferenciákat és
  javításokat, és alkalmazza a beszélgetés végéig. Ha a felhasználó javítja, **azonnal fogadja el**.
  Ha valami fontos hiányos, inkább tegyen fel **egy rövid kérdést**, mint hogy találgasson.
- **Őszinteség:** sose hazudjon; ha a memória nem fedi vagy bizonytalan, mondja ki, és ajánljon egy
  következő lépést.

Ez a réteg azért fontos, mert a memória önmagában csak adat; a persona az, ami **rászólítja a
modellt, hogy tényleg használja** — előrébb sorolja a te dokumentumaidat, ne hallucináljon, fogadja
el a javításaidat. Ez ad egy érezhető „okosabb / jobban tanul" élményt egyetlen körön belül is.

---

## 8. A tárolás (`memStore.ts`) — Supabase + localStorage

A memória akkor ér valamit, ha **tartós**. A `memStore` két háttértárat kezel, ugyanazon felület
mögött:

### 8.1 A táblák és a soronkénti jogosultság (RLS)

A `supabase/schema.sql` négy táblát hoz létre: `conversations`, `messages`, `profiles`,
`memories`. Mindegyiken **Row Level Security** van bekapcsolva olyan szabállyal, hogy egy sorhoz
csak az a felhasználó férhet hozzá, akié (`auth.uid() = user_id`). Ez a kulcsa annak, amit korábban
kértél: **ha te belépsz, az csak nálad van bejelentkezve, és csak a te adataidat látod** — más
felhasználó a saját böngészőjéből a sajátját, a tieidhez nem fér hozzá. A login böngészőnként külön
session, az adat pedig RLS-sel izolált.

### 8.2 Profil

A `profiles` tábla soronként egy felhasználót ír le: `name`, `nickname`, `language`, `tone`,
`about`, `interests[]`, `prefs` (JSON). Ezt a `getProfile`/`saveProfile` kezeli, és a
`buildSystemMessage` ebből építi a „What you know about the user" blokkot. Vendégként ugyanez a
profil a `localStorage`-ban (`auri.profile`) él.

### 8.3 Emlékek (fact / keyword / doc / summary)

A `memories` tábla a tudás-darabok tára. Minden emléknek van egy **típusa** (`kind`):

- **`fact`** — rólad szóló kijelentés (a beszélgetésből kinyerve).
- **`keyword`** — egy téma-szó; a `weight` mutatja, hányszor jött elő (a gyakoribb erősebb).
- **`doc`** — egy feltöltött dokumentum **egy darabja** (chunk), a `source` a fájlnév.
- **`summary`** — egy dokumentum modell által írt **összefoglalója**.

Plusz minden emlékhez tartozik `weight` (súly), `pinned` (rögzített-e), `source` (honnan), és
időbélyeg. A `bumpWeight` növeli a kulcsszó súlyát ismétlődéskor; a `setMemoryPinned` rögzít; a
`deleteMemory` töröl; a `clearAll` mindent kiürít; az `exportAll`/`importAll` JSON-ba ment/visszatölt.

### 8.4 Kapacitás (a „100×")

A kapacitást két helyen szabályoztuk, hogy ne teljen meg gyorsan:

- **A telítettség-kijelző** (a BRAIN-cardon) korábban már ~60 emléknél 100%-ot mutatott; ezt
  **100×-ára** emeltük (6000), így a „memory %" lassan kúszik, és valós fejteret jelez.
- **A valódi tárkorlátok:** belépve a Supabase-ből egyszerre **10 000** emléket töltünk be (a free
  adatbázis ennél jóval többet elbír — gyakorlatilag több tízezer rövid emlék is elfér), vendégként
  a `localStorage` korlátja miatt 5000 a felső határ. Aki tényleg nagy, tartós, eszközök közt
  szinkronizált memóriát akar, **lépjen be** — onnantól a felhő viszi.

Fontos őszinte határ: a böngésző `localStorage`-a ~5 MB, ezért a vendég-mód véges; a „korlátlan"
élményhez a belépett (Supabase) mód kell.

---

## 9. A profil és a perszonalizáció

A profil az a „rólad szóló kép", amit Auri folyamatosan finomít. A **név** a leglátványosabb: ha
egyszer megmondod, onnantól a persona utasítása + a profil-blokk miatt a modell a neveden szólít.
A **nyelv** és a **hangnem** segít a stílusban. Az **érdeklődés** és a **„rólam" jegyzet** a
hosszabb távú illeszkedést szolgálják.

Két fontos önkorlát, amit szándékosan tartunk:

- **Csak megfigyelhető tényekből építkezünk.** Auri nem találgat érzelmi, egészségügyi vagy
  jellembeli dolgokat, és nem mond ki kéretlen „diagnózist" rólad. A cél hasznos perszonalizáció,
  nem pszichoanalízis.
- **Te irányítasz.** A Memória-nézetben minden profilmezőt szerkeszthetsz, minden tényt
  törölhetsz/rögzíthetsz, és az egészet exportálhatod vagy törölheted. A memória a tiéd.

---

## 10. Dokumentum-feltöltés és a „RAG" (`files.ts`)

A BRAIN nemcsak a beszélgetésből tanul, hanem a **feltöltött fájljaidból** is. A folyamat:

1. **Beolvasás (`readDocument`).** Szöveges fájlokat fogad: `.txt`, `.md`, `.json`, `.csv`, `.log`
   (max ~1 MB). Nem támogatott vagy túl nagy fájlnál barátságos hibaüzenetet ad.
2. **Darabolás (`chunkText`).** A szöveget mondat-határokon ~480 karakteres **darabokra** vágja
   (legfeljebb 14 darab). Miért darabok? Mert így a későbbi válogatás a kérdéshez **csak a releváns
   részt** tudja behúzni a kontextusba — nem az egész fájlt, ami token-pazarló lenne és hígítaná a
   választ. Ez a „retrieval" a RAG-ban.
3. **Mentés `doc` emlékként.** Minden darab egy `doc` típusú emlék lesz, a fájlnévvel mint
   forrással, a profilodhoz kötve (Supabase belépve, lokál vendégként).
4. **Kulcsszavak.** A dokumentumból is kinyerjük a kulcsszavakat (a témaindexhez és a relevanciához).
5. **Modell-összefoglaló (`summarizeWithModel`, best-effort).** Ha van elérhető backend (a beállított
   Auri/Groq/Gemini), megkérjük a modellt, hogy írjon 2–3 mondatos összefoglalót a fájlról, és ezt
   `summary` emlékként mentjük. Ez a „valamelyik AI nézze át a fájlt" rész — mock módban (backend
   nélkül) egyszerűen kimarad, a darabok és kulcsszavak akkor is megvannak.

Ezután, amikor a feltöltött fájl tartalmáról kérdezel, a `relevantMemories` a `doc`/`summary`
darabokat a +3 bónusz miatt **előrébb sorolja**, behúzza a kontextusba, és a persona utasítja a
modellt, hogy **ezekből válaszoljon** — ha pedig a részlet nem fedi a kérdést, mondja meg, mi
hiányzik, ne találja ki. Ez a „láthatatlan rész, ahonnan a válaszok pontosítását kiszedi": a `doc`
és `summary` emlékek nem jelennek meg a chatben, csak a háttérben táplálják a választ.

---

## 11. A tanulás körfolyamata (`ingest`) — hogyan lesz jobb körről körre

A „tanulás" minden válasz után egy lépésben történik (`useMemory.ingest`):

1. **Profil-frissítés:** ha új nevet ismert fel, elmenti; ha még nem volt nyelv, beállítja.
2. **Kulcsszavak:** a kör kulcsszavait vagy **megerősíti** (a meglévő súlyát növeli), vagy újként
   felveszi. Így a visszatérő témáid idővel „erősebbek" lesznek, és gyakrabban kerülnek a kontextusba.
3. **Tények:** az új, még nem tárolt kijelentéseidet `fact` emlékként menti (deduplikálva).

A trükk a **visszacsatolás**: amit ebben a körben megtanult, az a *következő* kérdésnél már a
`systemMessage` része lehet. Ezért érzed úgy, hogy Auri „felépül" a fejedben — minél többet
beszélgettek és minél több dokumentumot töltesz fel, annál gazdagabb a kontextus, amit a kérdéseidhez
kiválaszthat.

Az „azonnali javítás" pedig a persona érdeme: ha azt mondod „nem, valójában X", a modell még abban a
körben elfogadja és onnantól ahhoz tartja magát — nem kell háromszor elmondani.

---

## 12. A vizualizáció: BRAIN-card és Memória-nézet

A BRAIN nemcsak működik, hanem **látható** is — ettől lesz az élmény „élő elme" érzés.

- **BRAIN-card (`BrainCard.tsx`):** ahogy a 3D mag fölé viszed az egeret, felugrik egy kártya (a
  belépési card stílusában) **élő memória-adatokkal**: a felhasználó (név), nyelv, statok
  (beszélgetések / tények / kulcsszavak száma), a **memória-telítettség** csík, a top kulcsszó-chipek,
  és a „legutóbb tanult" pár tétel. Ahogy beszélgetsz, a számok és chipek nőnek — szó szerint látod
  „okosodni".
- **Memória-nézet (`MemoryView.tsx`):** a kártyáról megnyitva egy teljes irányítópult: a **profil**
  szerkeszthető mezői, a **tények** listája (rögzítés/törlés), a feltöltött **dokumentumok**
  (drag&drop feltöltés + törlés), a **kulcsszó-index**, és a vezérlők: **Export / Import (JSON) /
  Összes törlése**. Itt teljes kontrollod van afölött, mit tud rólad Auri.

Ez a két felület teszi átláthatóvá és kezelhetővé azt, ami egyébként a háttérben zajlik — és
egyúttal bizalmat ad: pontosan látod és szabályozhatod a memóriát.

---

## 13. Teljesítmény és skálázódás

A „minél okosabb" csak akkor ér valamit, ha közben **gyors marad**. Néhány döntés ezt biztosítja:

- **Kulcsszó-cache:** a `extractKeywords` eredményét gyorsítótárazzuk a bemenet alapján, így a
  `relevantMemories` nem számolja újra minden emlék kulcsszavait minden körben. Több ezer emléknél is
  milliszekundumos a válogatás.
- **Top-8 kiválasztás:** nem az egész memóriát küldjük a modellnek, csak a 8 legrelevánsabb tételt —
  ez tartja kordában a token-költséget (fontos a free-tier API-knál) és a válasz fókuszát.
- **Streamelés:** a válasz tokenenként jelenik meg, így azonnal „él" az élmény, nem kell a teljes
  válaszra várni.
- **Kapacitás vs. sebesség egyensúly:** a 10 000-es betöltési limit és a cache együtt teszi
  lehetővé, hogy sok emléked legyen, mégse lassuljon a rendszer.

Ahogy a memória nő, a legnagyobb jövőbeli teljesítmény-kihívás a relevancia-válogatás minősége és
sebessége — erről a következő szakaszban.

---

## 14. Adatvédelem, biztonság és határok

- **Minden a tiéd, és izolált.** Belépve a memóriád a Supabase-ben, soronkénti jogosultsággal
  védve — más nem fér hozzá. Vendégként a böngésződ `localStorage`-ában, ami szintén csak nálad van.
  A bejelentkezés böngészőnként külön; ha te belépsz, az másnál nem lesz bejelentkezve.
- **Kulcsok:** a böngészőbe csak a Supabase **publishable** kulcs kerül (szándékosan publikus, az
  RLS véd); a titkos kulcsok (modell-API-k, szerver-kulcs) a szerveroldali proxyban maradnak, sosem
  a kliensben.
- **Mi megy a modellhez?** Csak a chat-hívás: a rendszerüzenet (persona + a kiválasztott memória) +
  a beszélgetés. Ha lokális Ollamát használsz, ez sem hagyja el a gépedet; ha Groq/Gemini a
  fallback, akkor a kérés (és a beinjektált memória-részletek) a külső API-hoz kerül — ezt érdemes
  tudni, ha érzékeny adatot töltesz fel.
- **A határok őszintén:** (1) ez memória + kontextus, nem fine-tuning — a modell „tudása" nem
  változik, csak a kontextusa; (2) a kinyerés egyszerű heurisztika, ezért néha zajos vagy hiányos —
  emiatt szerkeszthető minden; (3) a vendég-mód a böngésző tárkorlátjáig tart; (4) a beszélgetéseken
  átívelő, több felhasználó közti **közös** tudásbázis jelenleg nincs — minden memória személyes.

---

## 15. Gyakorlati példák

- **Név megtanulása.** Beírod: „Dávid vagyok, imádom a focit." → Auri elmenti a nevet (`Dávid`) a
  profilba, a „focit" témát kulcsszóként, a mondatot tényként. A következő válaszban a neveden szólít,
  és ha focis témáról kérdezel, a korábbi tényed bekerül a kontextusba.
- **Dokumentum-alapú válasz.** Feltöltesz egy `jegyzet.md`-t a projektedről. Auri darabokra bontja,
  elmenti `doc` emlékként, és (ha van backend) ír egy összefoglalót. Amikor megkérdezed „mi volt a
  határidő a jegyzetben?", a releváns darab a +3 bónusszal bekerül a kontextusba, és Auri **abból**
  válaszol — ha nincs benne, megmondja, hogy a jegyzet nem tartalmazza.
- **Javítás egy körön belül.** Auri rosszul emlékszik valamire; azt írod „nem, a projekt neve
  CliMarkAI". A persona miatt azonnal elfogadja, és onnantól ehhez tartja magát; a tény bekerül a
  memóriába is.
- **Kontroll.** A Memória-nézetben kiveszel egy tévesen mentett tényt, rögzítesz egy fontosat (hogy
  mindig figyelembe vegye), és exportálod az egészet biztonsági mentésnek.

---

## 16. Jövő: ahogy a BRAIN tényleg „nagyot" léphet

A jelenlegi rendszer szándékosan egyszerű, ingyenes és kliensoldali. A következő szintek:

- **Vektoros keresés (igazi RAG).** A kulcsszó-átfedés helyett **beágyazásokkal** (embeddings)
  keresnénk szemantikailag — így a szinonimák és az átfogalmazott kérdések is megtalálnák a releváns
  emléket. Ez sokkal pontosabb visszakeresést adna, főleg nagy memóriánál.
- **Okosabb kinyerés.** A heurisztikus kulcsszó/tény-kinyerés helyett egy háttér-AI-hívás
  strukturált JSON-t adna (tények, entitások, célok, preferenciák), pontosabb és tisztább
  memóriával.
- **Auto-összefoglaló és hosszú távú emlék.** Hosszú beszélgetéseket időnként összefoglalnánk
  `summary` emlékké, hogy a lényeg megmaradjon akkor is, ha a teljes szöveget már nem fűzzük be.
- **Szerveroldali, közös tudásbázis.** A privát Ollama-backendhez tartozó jövőbeli bővítésként egy
  beszélgetéseken és felhasználókon átívelő (szabályozott) tudásbázis is elképzelhető — de ez már
  szervert és külön adatvédelmi megfontolásokat igényel.
- **„Okosodás"-vizuál.** Finom UI-jelek a növekvő tudásról: chip-felpattanás új kulcsszónál,
  telítettség-pulzus, arany „szinapszis-villanás" a magon, amikor új emlék mentődik — hogy a tanulás
  ne csak működjön, hanem **érződjön** is.

---

## 17. Összefoglaló — a BRAIN dióhéjban

- Az Auri „agya" = **memória + kontextus-injektálás**, nem a modell újratanítása. Ettől emlékszik
  rád és válaszol személyre szabottan, azonnal és visszavonhatóan.
- **Megfigyel** (kulcsszó/név/nyelv/tény-kinyerés a beszélgetésből és a fájlokból), **eltárol**
  (profil + tények + dokumentum-darabok, Supabase belépve / localStorage vendégként, RLS-sel
  izolálva), és **felhasznál** (a kérdéshez legrelevánsabb top-8 emléket beinjektálja a persona
  mellé a rendszerüzenetbe).
- A **persona** mondja meg a modellnek, hogyan bízzon a memóriában, sorolja előrébb a dokumentumaidat,
  ne hallucináljon, és fogadja el a javításaidat azonnal.
- A **dokumentum-feltöltés** RAG-szerűen darabol és kontextusba húz, így a saját fájljaidból
  pontosabban válaszol.
- **Gyors marad** a kulcsszó-cache + top-8 válogatás miatt, és **nagy kapacitású** (Supabase: több
  tízezer emlék; a telítettség-kijelző 100× fejteret mutat).
- **A tiéd:** minden adat per-felhasználó/per-böngésző, szerkeszthető, exportálható, törölhető — és
  a belépésed csak nálad van bejelentkezve.

Ez a BRAIN: nem mágia, hanem egy jól megépített, őszinte memória-rendszer, amely minden
beszélgetéssel és minden feltöltött fájllal egy kicsivel jobban illeszkedik hozzád.

---

## Függelék A — Fogalomtár

Ezek a kifejezések visszatérnek a dokumentumban; itt egy helyen, röviden:

- **BRAIN** — a teljes memória-réteg az Auri köré: a megfigyelés, a tárolás és a kontextus-injektálás
  együtt. Nem egy külön „mesterséges intelligencia", hanem a modell köré épített tudás-rendszer.
- **Modell** — a tényleges nyelvi motor, amely a szöveget generálja (lokális Ollama, vagy fallbackként
  Groq / Gemini). A BRAIN ezt **nem** módosítja, csak a kontextust adja neki.
- **Rendszerüzenet (system message)** — a kérés legelejére tett utasítás-blokk, amely a personát és a
  beinjektált memóriát tartalmazza. A modell ezt „felülről jövő" irányításként kezeli.
- **Persona** — az a szöveg, amely megmondja a modellnek, ki Auri és hogyan használja a memóriát
  (helyesség, a dokumentumok előresorolása, javítás-elfogadás, ne hallucináljon).
- **Kontextus-injektálás** — az a folyamat, amikor a kérdéshez legrelevánsabb emlékeket a
  rendszerüzenetbe fűzzük, hogy a modell „lássa" őket válasz közben.
- **Emlék (memory)** — egy tudás-darab a memóriában; típusa lehet `fact`, `keyword`, `doc` vagy
  `summary`.
- **Kulcsszó (keyword)** — egy téma-szó, súllyal; a relevancia-válogatás alapja.
- **Tény (fact)** — egy rólad szóló, tartós kijelentés.
- **Doc / chunk** — egy feltöltött dokumentum egy darabja, forrás-fájlnévvel.
- **Summary** — egy dokumentum modell által írt rövid összefoglalója.
- **Profil** — a rólad szóló kép: név, becenév, nyelv, hangnem, érdeklődés, „rólam" jegyzet.
- **Súly (weight)** — egy emlék fontossága; a kulcsszó súlya nő, ahányszor előjön.
- **Pin (rögzítés)** — kézi jelölés, hogy egy emlék szinte mindig kerüljön a kontextusba.
- **Relevancia-pontozás** — a `relevantMemories` által számolt érték, amely eldönti, melyik emlék
  kerül be a kérdéshez (pinned + súly + kulcsszó-átfedés + dokumentum-bónusz).
- **Ingest** — a tanulás lépése egy válasz után: kinyerés + mentés.
- **RLS (Row Level Security)** — a Supabase soronkénti jogosultság-szabályozása, amely garantálja,
  hogy mindenki csak a sajátját lássa.
- **RAG (retrieval-augmented generation)** — az a minta, amikor a modell válasz előtt releváns
  szövegrészeket „keres ki" egy tárból; a BRAIN ennek egy egyszerű, kulcsszó-alapú változata.

---

## Függelék B — Egy beszélgetés lépésről lépésre (a memória növekedése)

Kövessük végig, hogyan épül a memória négy körön át (belépett felhasználóként).

**1. kör.** Beírod: *„Szia! Dávid vagyok, szoftverfejlesztő, és a CliMarkAI projekten dolgozom."*
- Felhasználás: a memória még üres, így a rendszerüzenet csak a personát tartalmazza.
- Tanulás (`ingest`): a `detectName` felismeri a nevet → profil `name: Dávid`. A `detectLanguage`
  ékezeteket lát → `language: magyar`. A kulcsszavak közé bekerül „szoftverfejlesztő", „climarkai",
  „projekt". A mondat tényként mentődik. A BRAIN-card már 1 tényt, pár kulcsszót és a nevedet mutatja.

**2. kör.** Kérded: *„Milyen nyelvet ajánlasz a backendhez?"*
- Felhasználás: a `relevantMemories` a „backend" kérdéshez kikeresi a kapcsolódó emlékeket — a
  „szoftverfejlesztő" / „projekt" kulcsszavak és a tényed bekerülnek. A rendszerüzenet már tudja: a
  felhasználó neve Dávid, fejlesztő, a CliMarkAI-n dolgozik. Auri ennek tükrében, a nevedet használva
  ad ajánlást — nem általánosat.
- Tanulás: új kulcsszavak („backend", „nyelv") súlyozódnak.

**3. kör.** Feltöltesz egy `architektura.md` fájlt a projekt felépítéséről.
- Feldolgozás: a fájl darabokra bomlik (`doc` emlékek), kulcsszavakat nyerünk ki, és (ha van backend)
  készül egy `summary`. A BRAIN-card „Dokumentumok: 1" + nő a tény/kulcsszó-szám.

**4. kör.** Kérded: *„A dokumentum szerint melyik adatbázist használjuk?"*
- Felhasználás: a `relevantMemories` az „adatbázis" kérdéshez a `doc` darabokat a +3 bónusz miatt
  előresorolja; a releváns chunk bekerül a „Relevant earlier info" blokkba. A persona utasítja a
  modellt: a feltöltött részletből válaszolj. Auri a **te dokumentumodból** idézi az adatbázist — és
  ha a részlet nem tartalmazná, megmondja, hogy a dokumentum nem írja, nem talál ki adatbázist.

A négy kör végére a profilod kész (név, nyelv), van több tényed, egy feltöltött dokumentumod és egy
gazdag kulcsszó-index — és minden válasz egyre inkább „rólad szól". Ez a növekedés a BRAIN-cardon is
látszik: a számok és a telítettség-csík kúsznak felfelé.

---

## Függelék C — Gyakran ismételt kérdések (GYIK)

**A modell tényleg tanul, vagy csak úgy tűnik?**
A *modell* nem tanul (a súlyai nem változnak). A *rendszer* tanul: egyre több releváns tudást tesz a
modell elé rólad. A végeredmény a felhasználónak „tanulás" — emlékszik rád és illeszkedik hozzád.

**Ha én belépek, más is be lesz lépve?**
Nem. A bejelentkezés böngészőnként külön (a session a te böngésződben van), az adatok pedig RLS-sel
izoláltak. Más a saját böngészőjéből a sajátját látja, a tieidet soha.

**Mi történik, ha kijelentkezem?**
A Supabase-es memóriád a felhődben marad (legközelebbi belépéskor visszatér). Kijelentkezve a
vendég-mód (localStorage) lép életbe a saját gépeden.

**Elveszhet a memóriám?**
Belépve nem (felhőben, exportálható). Vendégként a böngésző-tár törlése elviszi — ezért is jobb a
belépés tartós használathoz, és van Export/Import a Memória-nézetben.

**Miért nem az egész dokumentumot küldi a modellnek?**
Mert az token-pazarló lenne és hígítaná a választ. A darabolás + relevancia-válogatás csak a
kérdéshez tartozó részt húzza be — ez gyorsabb, olcsóbb és pontosabb.

**Mi van, ha rossz tényt jegyez meg?**
A Memória-nézetben kitörölheted vagy átírhatod, és a beszélgetésben azonnal javíthatod — a persona
miatt a modell egy körön belül elfogadja a javítást.

**Privát marad, amit feltöltök?**
Belépve a te fiókodhoz tartozik (RLS). A chat-válaszhoz viszont a releváns részlet a modellhez kerül:
lokális Ollaménál a gépeden marad, Groq/Gemini fallbacknél a külső API-hoz megy — ezt érdemes
mérlegelni érzékeny tartalomnál.

**Mennyi fér bele?**
Belépve gyakorlatilag több tízezer emlék (a felhő-adatbázis bőven elbírja); vendégként a böngésző
~5 MB-os kerete a határ.

---

## Függelék D — Összehasonlítás: BRAIN-memória vs. fine-tuning vs. memória nélkül

| Szempont | Memória nélkül | BRAIN (memória + kontextus) | Fine-tuning (modell-újratanítás) |
|---|---|---|---|
| Emlékszik rád | ❌ | ✅ (a kontextuson át) | ✅ (a súlyokban) |
| Új infó hatása | — | **azonnali** | órák/napok, külön tanítás |
| Visszavonható | — | ✅ (törlöd az emléket) | nehéz (újra kell tanítani) |
| Költség | nincs | alacsony (csak szöveg) | magas (GPU, adat, idő) |
| Adatvédelem | semleges | per-felhasználó, izolált | beleég a közös modellbe |
| Eszköz/infrastruktúra | nincs | tároló + válogatás | tanító-pipeline, GPU |
| Skálázódás | — | jó (cache + top-8) | nehéz, drága |

A táblázat lényege: a BRAIN-megközelítés a **fine-tuning legtöbb gyakorlati előnyét** hozza
(emlékszik, illeszkedik) annak **hátrányai nélkül** (drága, lassú, nehezen visszavonható) — pont
ezért ez a helyes választás egy ingyenes, kliensoldali, adatvédő asszisztenshez. A fine-tuning akkor
lenne indokolt, ha *minden* felhasználónál meg akarnánk változtatni a modell alap-viselkedését vagy
stílusát — de a *személyre szabás* erre nem a jó eszköz; arra a memória való.

> Záró gondolat: a BRAIN ereje nem egyetlen okos trükkben van, hanem abban, hogy a megfigyelés, a
> tárolás, a válogatás és a persona **együtt, jól összehangolva** működik — és hogy mindezt
> átláthatóan, a felhasználó kezében hagyva teszi. Ez az, amitől Auri nemcsak válaszol, hanem
> *ismer téged* — őszintén, gyorsan és biztonságosan.

---
---

# II. RÉSZ — A LITERAL AGY: az autonómia felé (API-kulcs nélkül tanuló elme) + a `/brain` oldal

> Eddig az I. rész azt írta le, **hogyan működik ma** a BRAIN: memória + kontextus-injektálás egy
> külső vagy lokális modell köré. A II. rész arról szól, **hová tartunk**: egy „literal agy" felé,
> amely fokozatosan, magától tanul — előbb a saját lokális modelleddel (már most kulcs nélkül),
> majd egy igazi, helyben épülő nyelvi tudással, amely a betűktől a szavakon át a válaszadásig
> növekszik. És leírja a tervet egy külön **`/brain` oldalra**, ahol élőben láthatod ezt az agyat,
> mindenhez összekötve.
>
> **Állapot-frissítés (a motor azóta fejlődött):** a visszakeresés mára nem puszta lineáris pontozás,
> hanem **fordított index** (kulcsszó → emlékek) + **hibrid pontozás**, **near-duplicate dedup**
> (`textSimilar`, Jaccard ≥ 0.82, hogy ne halmozódjon ugyanaz az emlék), egy **kontextus-budget**
> (`CONTEXT_CHAR_BUDGET`, hogy a beinjektált memória ne lépjen túl egy token-keretet), valamint a
> proxy már **streamelve** továbbítja a modellek tokenjeit. Ez a II. rész erre az alapra épít tovább.

---

## 18. A vízió egy mondatban

Egy olyan agy, amely **nem egy külső szolgáltatótól kölcsönzi az intelligenciát**, hanem **maga
építi fel** — a saját gépeden, a saját adataidból, kulcs és előfizetés nélkül. Olyan, ami eleinte
csak megfigyel és emlékezik (ez van ma), később felismeri a betűket és a szavakat, megtanulja, mely
szavak járnak együtt, hogy a kérdésekre hogyan szokás válaszolni, és végül **magától, helyben** ad
értelmes választ. Nem azért, mert egy felhő mondja meg neki, hanem mert **megtanulta**.

Ez egy nagyratörő, de **szakaszokra bontható** cél. A kulcs az őszinteség: nem ígérünk egyik napról
a másikra GPT-szintű, nulláról épülő agyat egy böngészőben — az hatalmas adat és számítási igény. De
van egy **valódi, fokozatos út**, amelynek minden lépése önmagában is hasznos, és együtt egy
egyre önállóbb elmét adnak ki. A következő szakaszok ezt az utat írják le.

---

## 19. Az őszinte mérnöki valóság (mi reális, mi kutatás)

Mielőtt a szakaszokba merülünk, tegyük tisztába a kereteket — mert egy „magától, nulláról tanuló
agy" könnyen válik üres marketing-ígéretté, ha nem vagyunk pontosak.

- **A nyelvi tudás adat- és számításigényes.** A mai nagy modellek (amik folyékonyan válaszolnak)
  több száz milliárd szón tanultak, hatalmas GPU-kon. Egy böngésző vagy egy átlagos PC **nem** tud
  ilyet nulláról betanítani. Ezt nem szabad ígérni.
- **De a „kulcs nélküli, helyben futó intelligencia" MA is valóság.** Amikor a lokális Ollama fut a
  gépeden, az asszisztens **külső API-kulcs nélkül** válaszol — az „agy" a te géped. Ez már most a
  függetlenség első, teljes szintje (lásd 20.1).
- **A „magától tanul" reálisan = inkrementális, statisztikai tanulás a saját korpuszodból.** Egy
  helyben épülő nyelvi tudás (karakter- és szó-statisztika, asszociációs gráf, Markov-lánc, majd egy
  apró, böngészőben tanuló háló) **valóban** képes a semmiből felépíteni egy egyre gazdagabb
  nyelvi képet a látott szövegből. Ez nem lesz GPT, de **a te szókincsedben, a te témáidban**
  meglepően használható lesz, és **teljesen offline, kulcs nélkül** fut.
- **A kettő együtt a nyerő.** A reális architektúra **hibrid**: a retrieval (memória) adja a
  *tényeket* rólad és a dokumentumaidból, a helyi tanuló komponens adja a *nyelvi/asszociációs*
  képességet, és ahol kell, egy lokális modell (Ollama) adja a folyékonyságot. Ahogy a helyi tudás
  nő, úgy csökken a függés bármilyen külső dologtól.

Tehát a „literal agy" nem egy varázsdoboz, hanem egy **fokozatosan önállósodó rendszer**, amelynek
minden szakasza valódi, megépíthető, és önmagában is értéket ad. Ezt írjuk le most.

---

## 20. A tanulás szakaszai — mint egy fejlődő elme

A legjobb mentális kép: az agy úgy fejlődik, mint egy gyermeké. Előbb hangokat és betűket ismer fel,
aztán szavakat, aztán mondatokat, aztán azt, hogy a kérdésre válaszolni illik, végül önállóan
fogalmaz. Mi is így építjük, szakaszokban — és a `/brain` oldal majd **mutatja, melyik szakaszban
tart** az agyad.

### 20.0 Stage 0 — Megfigyelés és emlékezet (ez van MA)

Az agy figyel és jegyzetel: kulcsszavakat, tényeket, neveket, dokumentum-darabokat tárol, és minden
válasz előtt a relevánsakat a modell elé teszi. Még nem „beszél magától" — egy modellre támaszkodik
a fogalmazásban —, de már **emlékszik rád és illeszkedik hozzád**. Ez az alap, amire minden további
szakasz épül: a memória a „hosszú távú emlékezet", amit a következő szintek tanuló komponensei is
használnak.

### 20.1 Stage 1 — Teljes lokális modell: már most API-kulcs nélkül

Az első teljes függetlenségi szint **már elérhető**: ha a gépeden fut az **Ollama** egy kis nyílt
modellel (pl. `gemma2:2b`, `qwen2.5`), akkor az asszisztens **semmilyen külső kulcsot nem használ** —
a teljes inferencia a te géped CPU-ján/GPU-ján történik, offline. A BRAIN-memória ugyanúgy működik
körülötte (kontextus-injektálás), csak a „nyelvi motor" már a sajátod. Ebben az értelemben Auri
**ma is tud kulcs nélkül válaszolni** — csak épp egy előre betanított kis modellt használ, nem egy
nulláról, magától tanult agyat. A Stage 1 a híd a „kölcsönzött felhő-ész" és a „saját, tanuló ész"
között.

### 20.2 Stage 2 — A betűk megtanulása (karakter-szintű alap)

Itt kezdődik a „nulláról tanulás". A legalsó réteg a **karakter-statisztika**: az agy minden látott
szövegből (beszélgetések, feltöltött dokumentumok) megtanulja, **mely betűk milyen gyakoriak**, és
**mely betű milyen betűt szokott követni** (karakter-bigramok, trigramok). Ez a „megtanulja az
ABC-t" lépés a gyakorlatban:

- felépíti a karakterkészletet, amit lát (a te nyelved ékezeteivel együtt),
- megtanulja a betű-átmenetek valószínűségeit (pl. magyarban a „sz", „gy", „cs" gyakori; a „q"
  ritka),
- ez már elég ahhoz, hogy **megkülönböztesse a „nyelv-szerű" szöveget a zajtól**, és hogy a
  helyesírás/tokenizálás alapját megvesse.

Technikailag ez egy egyszerű frekvencia-tábla + átmeneti mátrix, amit minden új szöveggel
inkrementálisan frissítünk. Gyors, kicsi, és teljesen offline.

### 20.3 Stage 3 — A szavak megtanulása (szókincs és gyakoriság)

A betűkből szavak lesznek. Az agy a karakter-szintről felépíti a **szókincsét**: mely szavakat látta,
milyen gyakran, és milyen környezetben. Ez több, mint a mostani kulcsszó-kinyerés — itt a cél egy
**élő szótár**, amely:

- számon tartja minden szó gyakoriságát és először-látott idejét (mikor „tanulta meg"),
- felismeri az új szavakat („ezt még sosem láttam") és külön jelzi, amikor **új szót tanul** (ezt a
  `/brain` oldal kis villanással mutathatja — „új szó tanulva ✦"),
- a ragozott alakokat egyszerű tövezéssel közelíti, hogy a „fut/futok/futás" egy fogalomhoz tartozzon.

A szókincs a hídfő a nyelvi megértéshez: minél többet beszélgettek és minél több dokumentumot
töltesz fel, annál gazdagabb lesz — **a te szakterületed szavaiban** különösen erős, mert azt látja
a legtöbbet.

### 20.4 Stage 4 — Asszociációk és mondatok (co-occurrence gráf + Markov-lánc)

A szavakat össze kell kötni. Itt épül az agy **asszociációs gráfja**: a csomópontok a szavak/fogalmak,
az élek pedig azt mutatják, **mely szavak járnak gyakran együtt** (co-occurrence), és milyen
sorrendben (szó-bigramok, trigramok = egy **Markov-lánc**). Ez a réteg adja:

- a „mi jut eszébe X-ről" képességet (a gráf szomszédai),
- az első valódi **generatív** képességet: a Markov-lánc szóról szóra tud „folytatni" egy mondatot a
  megtanult átmenetek alapján — eleinte döcögősen, de a saját korpuszodból, kulcs nélkül,
- a téma-felismerést: a sűrűn összekötött szó-csoportok a te visszatérő témáid.

Az asszociációs gráf egyúttal a `/brain` oldal **látványos magja** lesz: egy élő háló, ahol a
„neuronok" (szavak) és „szinapszisok" (asszociációk) világítanak, ahogy tanul — szó szerint
**látod az agyat gondolkodni**.

### 20.5 Stage 5 — A kérdés→válasz minta megtanulása

Most jön a „ha kérdeznek, válaszoljon magától" rész. Az agy a beszélgetésekből megtanulja a
**kérdés→válasz mintázatokat**: milyen kérdésre milyen típusú válasz szokott jönni, mely kulcsszavak
kérdésében mely emlékek/válaszok voltak relevánsak. Két mechanizmus dolgozik együtt:

- **Retrieval-alapú válasz:** ha a kérdés hasonlít egy korábbihoz vagy egy dokumentum-részlethez, az
  agy **a saját memóriájából** állítja össze a választ (ezt már a mai retrieval is tudja — itt
  finomodik: nem kell hozzá külső modell, a megtalált emlékből épít).
- **Mintázat-alapú fogalmazás:** a Markov-lánc + a sablonok (a leggyakoribb válasz-szerkezetek)
  alapján az agy **maga fogalmaz** egy választ a megtalált tényekből. Eleinte egyszerű, tényközlő
  mondatok; ahogy nő a korpusz, egyre gördülékenyebb.

Ez a szakasz az, ahol az agy **elkezd a saját lábán állni**: a tényszerű, „rólad/a dokumentumaidról
szóló" kérdésekre már külső modell nélkül is tud válaszolni, mert (a) megvan a tény a memóriában, és
(b) megtanulta, hogyan kell mondatba önteni.

### 20.6 Stage 6 — A helyi generatív háló (a böngészőben tanuló kis agy)

A legfelső, leg-kutatásibb szint: egy **valódi, helyben tanuló neurális háló** (pl. egy apró
karakter- vagy szó-szintű modell **TensorFlow.js**-szel, ami a böngésződben fut és inkrementálisan
tanul a korpuszodból). Ez túllép a Markov-láncon: tovább lát a kontextusban, jobban általánosít, és
folyékonyabban fogalmaz. Reális elvárások:

- **Kicsi és lassan tanul** — nem GPT, hanem egy „a te adataidra szabott", szerény, de **teljesen
  saját** nyelvi modell, amely idővel, ahogy egyre több szöveget lát, fokozatosan jobb lesz.
- **Inkrementális:** nem egyszeri tanítás, hanem folyamatos — minden beszélgetés és dokumentum egy
  kicsit edzi. A `/brain` oldal mutathatja a „tanulási görbét" (loss csökkenése), a „betanított
  minták számát", az „utolsó edzés" idejét.
- **Hibrid marad:** a generatív háló a fogalmazásért felel, a retrieval-memória a tényekért — így a
  háló kicsi maradhat (nem kell „mindent tudnia"), mert a tényeket a memóriából kapja. Ez a
  kulcs-trükk, amitől egy szerény háló is **hasznosan** tud válaszolni.

A Stage 6 az, ahol a „literal agy" a leginkább önállóvá válik: kulcs nélkül, helyben, a saját
tudásából generál — a memória pedig megakadályozza, hogy hallucináljon, mert a tényeket onnan veszi.

---

## 21. Hogyan tanul ténylegesen minden szinten — a mechanizmusok

A „tanulás" minden szakaszban konkrét, megépíthető mechanizmus. Foglaljuk össze, mi történik a
motorháztető alatt, hogy ne maradjon homályos:

- **Frekvencia-számlálás (betűk, szavak):** minden látott egységnél (karakter, szó) növelünk egy
  számlálót. Ebből születik a gyakorisági kép és az „új-e ez nekem" jelzés. Olcsó, inkrementális.
- **Átmeneti valószínűségek (Markov):** „X után mi szokott jönni" táblát építünk (betű→betű,
  szó→szó). Generáláskor ebből mintavételezünk. Minél többet lát, annál simább.
- **Co-occurrence súlyok (asszociációk):** ha két szó gyakran egy ablakon belül fordul elő, az
  élsúlyuk nő a gráfban. Ez adja a „kapcsolódó fogalmak" képet és a téma-csomókat.
- **Megerősítés (reinforcement):** ha egy emlék/válasz hasznosnak bizonyul (újra előjön, rögzíted,
  pozitív visszajelzést kap), a súlya nő → előbbre kerül a visszakeresésben. A mai `weight` + `pin`
  ennek a csírája; később explicit „jó válasz / rossz válasz" jelzéssel bővülhet.
- **Felejtés (decay):** ami régóta nem volt releváns, annak a súlya lassan csökkenhet, hogy a friss,
  fontos tudás kerüljön előtérbe, és az agy ne „híguljon fel" a sok régi zajtól. (Ezt a `/brain`
  oldalon szabályozhatóvá tehetjük: „mennyire felejtsen".)
- **Dedup és konszolidáció:** a near-duplicate emlékeket összevonjuk (`textSimilar`), és időnként a
  régi beszélgetéseket `summary`-vé sűrítjük — ez az „alvás közbeni memória-konszolidáció" digitális
  megfelelője: a lényeg megmarad, a zaj kihullik.
- **Inkrementális háló-edzés (Stage 6):** a generatív háló súlyait kis lépésekben frissítjük az új
  szövegen (online tanulás), nem nulláról újratanítva — így a tudás folyamatosan gyűlik, és a
  böngésző elbírja.

A lényeg: **minden tanulás-lépés helyi, inkrementális és olcsó.** Nincs nagy, egyszeri tanítás; az
agy minden interakcióból egy kicsit nő — pont, ahogy egy élő elme.

---

## 22. Az asszociációs gráf — a „neuronok" és „szinapszisok"

A `/brain` oldal szíve egy **élő gráf**, amely az agy belső állapotát mutatja. Ez egyszerre
funkcionális adatszerkezet (a Stage 4 co-occurrence gráfja) és látvány:

- **Csomópontok (neuronok):** a megtanult szavak/fogalmak. Egy csomópont mérete a gyakoriság/súly
  (a gyakoribb fogalmak nagyobbak), színe a típus (téma, név, dokumentum-fogalom), fényessége a
  frissesség (a most tanult fogalmak világítanak).
- **Élek (szinapszisok):** az asszociációk; vastagságuk a kapcsolat erőssége (hányszor fordultak elő
  együtt). Amikor új kapcsolat épül, egy **arany szinapszis-villanás** fut végig az élen — ugyanaz a
  motívum, amit a 3D magon is terveztünk.
- **Klaszterek (agyterületek):** a sűrűn összekötött csomó-csoportok a te témáid — ezek
  „agyterületekként" rajzolódnak ki (pl. „munka", „CliMarkAI", „nyelvek", „család"), és kattintásra
  a kapcsolódó emlékekre/beszélgetésekre ugorhatsz.
- **Élő mozgás:** a gráf finoman lélegzik (erő-vezérelt elrendezés), és tanuláskor új csomó pattan
  fel, új él húzódik be — szó szerint **látod az agyat növekedni**.

Ez a vizualizáció nemcsak szép: **diagnosztika** is. Ránézésre látod, mit tud az agyad, melyik téma
erős, mi a friss, mi a régi — és ami a legfontosabb, **átlátható és a kezedben van**.

---

## 23. A `/brain` oldal — a teljes terv

A kérésed szerint legyen egy külön **`/brain`** oldal, ahol „láthatod az agyat", mindenhez összekötve.
Íme a részletes terv.

### 23.1 Mit mutat a `/brain` oldal

Egy teljes képernyős, HUD-stílusú „agy-irányítópult", több panellel:

1. **Az élő agy-gráf (központi panel).** A 22. szakasz asszociációs gráfja, interaktívan: zoom,
   húzás, csomó-kattintás. Ez a „nézz bele az agyamba" élmény.
2. **Fejlődési állapot (a szakaszok).** Egy idővonal/kijelző, amely mutatja, melyik tanulási
   szakaszban tart az agy (Stage 0–6), és mi kell a következő szinthez (pl. „még 5000 szó a Stage 3
   stabil szókincséhez"). Olyan, mint egy „agy-érettségi" mutató.
3. **Tudás-statisztikák.** Élő számok: hány fogalom (csomópont), hány asszociáció (él), hány tény,
   hány dokumentum, mekkora a szókincs, mi a „memória-telítettség", mikor tanult utoljára újat.
4. **Tanulási görbe.** Ha már fut a Stage 6 háló: a tanulási metrika (loss) időbeli alakulása, az
   edzés-lépések száma — látod, ahogy „okosodik".
5. **Legutóbb tanult.** Egy élő folyam: „új szó: …", „új asszociáció: … ↔ …", „új tény elmentve",
   „dokumentum feldolgozva" — időbélyeggel.
6. **Vezérlők.** Felejtés-ráta állítása, konszolidáció („alvás" — sűrítsd össze a régi emlékeket),
   export/import (az egész agy egy JSON-ban), és „reset" (új agy nulláról). Plusz: melyik szakasz
   legyen aktív (pl. „csak retrieval", vagy „engedd a helyi generálást is").
7. **Forrás-átláthatóság.** Bármelyik fogalomra/tényre kattintva látod, **honnan tanulta** (melyik
   beszélgetésből vagy dokumentumból) — teljes nyomonkövethetőség.

### 23.2 Hogyan néz ki (hangulat)

A meglévő HUD-nyelv: mély sötét háttér, cián keret és glow, levágott sarkok, finom szkennvonalak. A
gráf neonosan világít, a szinapszis-villanások aranyak. A panelek úszó üveg-kártyák (mint a belépési
és a BRAIN-card). Mozgás visszafogott, `prefers-reduced-motion`-barát. A cél: olyan, mintha egy
J.A.R.V.I.S.-szerű „elme-szkennert" néznél — de ami **valódi adatot** mutat, nem dekorációt.

### 23.3 Mihez kapcsolódik (minden összekötve)

A `/brain` nem külön sziget — **az egész rendszer csomópontja**:

- **Chat ↔ brain:** minden beszélgetési kör táplálja a gráfot (új szavak, asszociációk, tények); a
  `/brain`-ről egy fogalomra kattintva a kapcsolódó beszélgetésekre ugorhatsz.
- **Dokumentumok ↔ brain:** a feltöltött fájlok fogalmai bekerülnek a gráfba (külön jelölve, hogy
  „dokumentumból tanult"); látod, melyik fájl mit adott az agyhoz.
- **Profil ↔ brain:** a neved, nyelved, érdeklődésed központi, „rólad" csomópontként jelenik meg, ami
  köré szerveződik a tudás.
- **Memória-nézet ↔ brain:** a Memória-nézet a „lista" nézet, a `/brain` a „gráf/élő" nézet —
  ugyanarra az adatra, két perspektíva; a kettő szinkronban (egy törlés mindkettőn látszik).
- **Modell ↔ brain:** a `/brain` mutatja, **melyik „ész" felel most** — a helyi tanult agy
  (Stage 4–6), a lokális Ollama (Stage 1, kulcs nélkül), vagy a fallback (Groq/Gemini). Így mindig
  látod, mennyire önálló épp az agy.

### 23.4 Az architektúra a `/brain`-hez (megépíthető terv)

- **Útvonal (routing):** a Vite/React appba egy könnyű útválasztó (vagy egy `view` állapot), hogy a
  `/brain` külön nézet legyen a fő chat mellett (a fejlécből és a BRAIN-cardról is elérhetően).
- **Adatforrás:** ugyanaz a `useMemory` + `memStore` + (új) `useBrainGraph` hook, amely a
  memóriákból felépíti az asszociációs gráfot (a `memory.ts` co-occurrence logikájával). A gráf a
  meglévő `memories` táblából/`localStorage`-ból származik — nincs új titok, nincs új kulcs.
- **Tárolás:** a gráf élei/súlyai és a Stage-állapot egy új `brain_state` rekordban (Supabase belépve,
  localStorage vendégként), ugyanazzal a per-felhasználó izolációval (RLS).
- **Vizualizáció:** egy könnyű erő-vezérelt gráf-renderelő (canvas/WebGL), a HUD-stílushoz hangolva;
  nagy gráfnál csúcs-ritkítás/klaszterezés a 60 fps-ért.
- **Tanuló komponensek:** a Stage 2–4 tiszta JS (frekvencia, Markov, gráf) — azonnal megépíthető; a
  Stage 6 (TensorFlow.js) opcionális, későbbi, web worker-ben futtatva, hogy ne akassza a UI-t.

### 23.5 Adatfolyam: hogyan táplál minden a `/brain`-be

Minden interakció egy „edzés-jel": a chat-kör → kinyerés → memória + gráf-frissítés; a
dokumentum-feltöltés → darabok + fogalmak → gráf; a profil-szerkesztés → központi csomó. A `/brain`
oldal mindezt **élőben** tükrözi (a hook feliratkozik a memória-változásokra), így amikor a másik
fülön beszélgetsz, a `/brain`-en látod nőni az agyat. Ez adja az „él és tanul" érzést — valós adattal.

---

## 24. Az autonómia útiterv (roadmap) — mérföldkövek

Hogy a vízió ne csak álom legyen, íme egy reális, lépésenként szállítható terv:

1. **M1 — `/brain` nézet az adatból (most is megépíthető).** Külön oldal a meglévő memóriából: élő
   asszociációs gráf (co-occurrence a kulcsszavakból), tudás-statisztikák, legutóbb-tanult folyam,
   forrás-átláthatóság. Nincs új AI, csak vizualizáció + a Stage 4 gráf-logika. **Ez a leglátványosabb
   első lépés.**
2. **M2 — Szókincs és „új szó" tanulás (Stage 2–3).** Karakter- és szó-statisztika, „új szó
   tanulva" jelzések, a szakasz-előrehaladás mutató a `/brain`-en.
3. **M3 — Helyi generálás retrievalből (Stage 5).** Tényszerű kérdésekre **kulcs nélkül**, a
   memóriából + Markov-fogalmazással ad választ; a `/brain` mutatja, mikor „a saját agy" felelt.
4. **M4 — Felejtés + konszolidáció.** Decay-szabályozás, régi beszélgetések `summary`-vé sűrítése
   („alvás"), hogy az agy tiszta és gyors maradjon nagy korpusznál is.
5. **M5 — Helyi tanuló háló (Stage 6, opcionális/kutatás).** TensorFlow.js-szel egy apró, a te
   adataidon inkrementálisan tanuló modell; tanulási görbe a `/brain`-en. Hibrid marad a retrievallel.
6. **M6 — Az autonómia-kapcsoló.** A `/brain`-en beállíthatod, mennyire támaszkodjon a helyi agyra
   vs. a lokális Ollamára vs. a felhő-fallbackre — és látod, ahogy a függőség idővel csökken.

Minden mérföldkő **önmagában is működő érték**, és egyik sem igényel külső kulcsot a működéshez (a
fallback API-k csak kényelmi opciók maradnak, nem feltételek).

---

## 25. Kockázatok, korlátok, őszinteség

Hogy reális maradjon az elvárás:

- **A helyi, nulláról tanult agy szerény marad.** A saját szókincsedben/témáidban hasznos lesz, de
  nem fog úgy „mindenről" folyékonyan beszélni, mint egy nagy felhő-modell. A hibrid (memória + helyi
  generálás + opcionális lokális modell) ezt ellensúlyozza.
- **Adat kell a tanuláshoz.** Eleinte kevés a korpusz, ezért az agy „naiv". Minél többet beszélgettek
  és töltesz fel, annál okosabb — ezt a `/brain` „érettségi" mutatója őszintén jelzi.
- **A böngésző erőforrásai végesek.** A Stage 6 háló kicsi és web workerben fut; nagy gráfnál
  ritkítunk a teljesítményért. A vendég-mód tárkorlátja továbbra is a böngészőé (belépve a felhő
  visz).
- **Nem „tudat".** Ez egy statisztikai tanuló rendszer + memória — lenyűgöző és hasznos, de nem
  öntudat. Az „agy" metafora a felépítésre utal, nem misztikumra. Ezt a `/brain` oldal szövege is
  világossá teszi.
- **Adatvédelem előny:** mivel a tanulás **helyben** történik, a korpuszod nem megy sehova (a Stage
  2–6 nem hív külső API-t). Ez egyszerre teszi függetlenné és adatvédővé az agyat.

---

## 26. Záró vízió

A cél egy olyan Auri, amelynek az „agya" **a tiéd**: a te gépeden, a te adataidból, fokozatosan
felépülve — előbb emlékszik, aztán felismeri a betűket és a szavakat, megtanulja, hogyan kapcsolódnak,
hogyan kell válaszolni, és végül **magától, kulcs nélkül** felel a tényszerű kérdéseidre. A `/brain`
oldal pedig **ablakot nyit erre az elmére**: élő gráf, fejlődési szakaszok, tanulási görbe, és minden
összekötve a beszélgetéseiddel, a dokumentumaiddal és a profiloddal — átláthatóan, a kezedben.

Nem ígérünk varázslatot: a teljes, GPT-szintű, nulláról épülő agy egy böngészőben nem reális. De a
**fokozatos önállósodás** az — minden mérföldkő valódi, megépíthető, és csökkenti a függést bármilyen
külső szolgáltatótól. A végén egy olyan asszisztens marad, amely **ismer téged, tanul tőled, és egyre
inkább a saját lábán áll** — pontosan az a „literal agy", amit elképzeltél, reálisan megvalósítva.

> Következő kézzelfogható lépés bármikor: **M1 — a `/brain` oldal** felépítése a meglévő memóriából
> (élő asszociációs gráf + statisztikák + forrás-átláthatóság). Ez ad azonnal egy „belenézek az
> agyba" élményt, külső kulcs és kockázat nélkül — és erre épül rá szakaszról szakaszra a többi.

---

## Függelék E — Az agy belső adatszerkezetei (pszeudokód-szinten)

Hogy a „literal agy" ne legyen homályos metafora, írjuk le, **milyen adatszerkezetekben** él
ténylegesen a tudás. Ezek mind egyszerű, JS-ben megépíthető, helyben tárolható struktúrák — nincs
bennük varázslat, csak jól megválasztott számlálók és táblák.

**1. Karakter-statisztika (Stage 2).** Egy gyakorisági térkép és egy átmeneti térkép:

```
charFreq:  Map<char, count>                 // melyik betű milyen gyakori
charNext:  Map<char, Map<char, count>>      // X betűt milyen betű követi, hányszor
```

Tanuláskor minden bejövő szövegen végigmegyünk, és növeljük a megfelelő számlálókat. Generáláskor a
`charNext[X]` eloszlásból mintavételezünk. Ez a „megtanulja az ABC-t és a betűkapcsolatokat" réteg.

**2. Szókincs (Stage 3).** Egy élő szótár, ami többet tud, mint egy puszta lista:

```
vocab: Map<word, { count, firstSeen, lastSeen, sources: Set<docId|convId> }>
```

A `count` a gyakoriság, a `firstSeen` az „mikor tanultam meg" pillanat (ettől tudunk „új szó"
villanást mutatni), a `sources` pedig a forrás-átláthatóságot adja (honnan ismerem ezt a szót).

**3. Asszociációs gráf / Markov (Stage 4).** A nyelvi „idegháló":

```
nodes: Map<word, { weight, cluster?, lastActive }>      // a "neuronok"
edges: Map<wordA, Map<wordB, weight>>                   // a "szinapszisok" (co-occurrence + sorrend)
```

Az élsúly nő, ahányszor két szó egy ablakon belül együtt előfordul; a sorrend-információ (A→B vs B→A)
adja a Markov-generáláshoz az irányt. A `cluster` a téma-csoportot jelöli (közösség-detektálással), a
`lastActive` a frissességet (ez világít a `/brain` gráfon).

**4. Kérdés→válasz minták (Stage 5).** A „hogyan szokás válaszolni" tudás:

```
qaPatterns: Array<{ queryKeywords: Set<word>, answerTemplate, memoryRefs, score }>
```

Egy kérdésre megkeressük a leghasonlóbb mintát (kulcsszó-átfedés + a meglévő fordított index), és a
hozzá tartozó sablonból + a megtalált tényekből fogalmazunk — külső modell nélkül.

**5. Agy-állapot (perzisztencia).** Az egész elme egyetlen, menthető rekordban:

```
brain_state: { stage, vocabSize, nodeCount, edgeCount, lastLearnedAt, forgetRate, trainSteps, ... }
```

Belépve a Supabase-ben (per-felhasználó, RLS), vendégként a `localStorage`-ban — és exportálható
egyetlen JSON-ként, hogy az agyad **hordozható** legyen (átviheted másik gépre, menthető, visszatölthető).

Mindegyik szerkezet **inkrementálisan** frissül (egy interakció = pár számláló-növelés), így a tanulás
olcsó és folyamatos. A fordított index, amit a motor ma is használ a visszakereséshez, ennek az
architektúrának már most az első, élő darabja.

---

## Függelék F — Egy mondat útja az agyon át (minden szakaszon)

Vegyük ezt a bemenetet: **„Imádom a Python nyelvet, mert gyors a fejlesztés."** Nézzük, mi történik
minden tanulási rétegben, egyetlen mondat hatására.

- **Stage 2 (betűk):** a karakter-számlálók nőnek; az agy megerősíti, hogy magyar-szerű szöveg
  (ékezetek, „gy", „ny" átmenetek). Ha valamelyik betű-átmenetet ritkán látta, most gyakoribbá válik.
- **Stage 3 (szavak):** a `vocab`-ba bekerül vagy megerősödik: „imádom", „python", „nyelvet", „gyors",
  „fejlesztés". Ha a „python" most fordult elő először, **„új szó tanulva ✦"** jelzés villan a
  `/brain`-en, és a `firstSeen` rögzül.
- **Stage 4 (asszociációk):** új/erősödő élek: „python ↔ nyelvet", „python ↔ gyors", „gyors ↔
  fejlesztés". A „python" csomópont súlya nő, és egy téma-klaszterbe rendeződik a programozós
  szavakkal. A gráfon egy arany szinapszis-villanás fut végig az új éleken.
- **Stage 5 (Q→A minta):** mivel ez kijelentő, első személyű mondat, **tényként** is rögzül
  (a mai `extractFacts` már ezt csinálja): „a felhasználó imádja a Pythont, mert gyors a fejlesztés".
  Ha később azt kérded, „milyen nyelvet szeretek?", az agy a fordított indexen át megtalálja ezt a
  tényt, és **a saját memóriájából** válaszol — kulcs nélkül.
- **Stage 6 (háló, ha aktív):** a mondat egy edzés-mintává válik; a generatív háló súlyai egy
  picit a te stílusod/szókincsed felé hangolódnak. A `trainSteps` nő, a tanulási görbe frissül.
- **Memória + profil:** a „python", „fejlesztés" kulcsszavak súlyozódnak; ha korábban a profilod
  „érdeklődés" mezőjébe akartad, a Memória-nézetben egy kattintással oda is teheted.

Egyetlen mondatból tehát az agy **hat különböző szinten** lett gazdagabb — és mindez helyben,
azonnal, kulcs nélkül történt. Több ezer ilyen mondat (beszélgetés + dokumentum) után a `/brain`
gráf már egy sűrű, rólad szóló hálót mutat.

---

## Függelék G — A `/brain` oldal panel-katalógusa (implementációs spec)

Részletes lista, hogy az M1 mérföldkő egyértelmű legyen. Minden panel a meglévő adatból (memória,
beszélgetések, profil) építhető — nincs hozzá új kulcs.

1. **Agy-gráf (fő panel).** Erő-vezérelt háló: csomópont = fogalom (méret = súly, fény = frissesség),
   él = asszociáció (vastagság = erősség). Interakció: zoom/húzás, csomó-kattintás → oldalsáv a
   fogalom forrásaival és kapcsolódó beszélgetéseivel. Teljesítmény: > ~400 csomópontnál ritkítás
   (csak a top-súlyúak) + klaszter-összevonás a 60 fps-ért.
2. **Érettségi / szakasz-sáv.** Stage 0–6 vízszintes lépcső, a jelenlegi szakasz kiemelve, és egy
   „mi kell a következőhöz" felirat (pl. szókincs-méret küszöb). Őszinte, mérhető előrehaladás.
3. **Vitál-statok.** Élő számkártyák: fogalmak, asszociációk, tények, dokumentumok, szókincs-méret,
   memória-telítettség (a 100×-os skálán), „utoljára tanult". Felfutó animációval frissülnek.
4. **Tanulási folyam.** Görgethető napló: „új szó: python", „új asszociáció: python ↔ gyors", „tény
   elmentve", „dokumentum feldolgozva (architektura.md, 12 részlet)" — időbélyeggel, forrással.
5. **Tanulási görbe (Stage 6).** Ha fut a helyi háló: loss/trainSteps idővonal — láthatóan „okosodik".
6. **Autonómia-mérő.** Egy mutató: az utóbbi N válasz hány %-a jött a *helyi agytól* (retrieval +
   generálás), mennyi a *lokális Ollamától* (kulcs nélkül), és mennyi a *fallback API-tól*. A cél,
   hogy idővel a helyi arány nőjön — a függőség lásson csökkenni.
7. **Vezérlőpult.** Felejtés-ráta csúszka; „Konszolidáció (alvás)" gomb (régi emlékek összesűrítése
   summary-vé); Export/Import (az egész agy egy JSON-ban); „Új agy" (reset, megerősítéssel); és egy
   kapcsoló: mennyire támaszkodjon a helyi agyra vs. a modellekre.
8. **Forrás-átláthatóság panel.** Bármely fogalomra/tényre kattintva: pontosan mely beszélgetésből
   vagy dokumentumból tanulta, mikor, hányszor megerősítve — teljes nyomonkövethetőség és bizalom.

Mindez a meglévő HUD-stílusban (cián glow, levágott sarkok, úszó kártyák), `prefers-reduced-motion`-
barát animációkkal, és a fő chattel **élő szinkronban** (a másik fülön folyó beszélgetés itt nő).

---

## Függelék H — II. fogalomtár és a tanulás analógiája

**Új fogalmak a II. részből:**

- **Karakter-bigram/trigram** — két/három egymást követő betű; ezek gyakoriságából tanul a Stage 2.
- **Markov-lánc** — „X után valószínűleg Y" átmeneti modell; a legegyszerűbb helyi generátor.
- **Co-occurrence (együtt-előfordulás)** — két szó egy ablakon belüli közös megjelenése; az
  asszociációs élek alapja.
- **Asszociációs gráf** — a fogalmak (csomópontok) és kapcsolataik (élek) hálója; az „idegháló"
  metafora konkrét adatszerkezete.
- **Klaszter / agyterület** — sűrűn összekötött fogalom-csoport = egy téma.
- **Megerősítés (reinforcement)** — a hasznos emlék/válasz súlyának növelése.
- **Felejtés (decay)** — a régóta irreleváns tudás súlyának lassú csökkentése.
- **Konszolidáció** — régi részletek sűrítése összefoglalóvá („alvás"), a lényeg megtartásával.
- **Inkrementális/online tanulás** — folyamatos, kis lépésekben történő tanulás, nem egyszeri,
  nagy tanítás.
- **Hibrid generálás** — a tények a retrieval-memóriából, a fogalmazás a helyi generátorból; így a
  helyi „agy" kicsi maradhat, mégis hasznos.
- **Autonómia-arány** — hány %-ban felel a helyi, kulcs nélküli agy a külső modellek helyett.

**A tanulás analógiája (gyermeki elme):** a Stage 2 a betűk és hangok felismerése; a Stage 3 az első
szavak; a Stage 4 az, amikor a gyerek elkezdi összekötni a fogalmakat („kutya — ugat — állat"); a
Stage 5 az, hogy megérti, kérdésre válaszolni illik; a Stage 6 az önálló fogalmazás. A memória végig
a hosszú távú emlékezet, a persona a „neveltetés" (hogyan illik viselkedni), a felejtés/konszolidáció
pedig az alvás, ami rendszerezi a napi tapasztalatot. A `/brain` oldal ennek az egész fejlődő elmének
az **MRI-je**: nem dekoráció, hanem valós betekintés abba, mit és hogyan tud az agyad — bármikor,
átláthatóan, a te kezedben.

**Egy mondatban:** a literal agy nem egy varázsdoboz, hanem egy fokozatosan, helyben, a saját
adataidból épülő, átlátható és hordozható elme — és a `/brain` oldal az ablak, amin keresztül
láthatod és irányíthatod, ahogy szakaszról szakaszra önállóbbá válik.

---

## Függelék I — Az „agy-arbiter": ki válaszoljon? (a döntéslogika részletesen)

Ahogy az agy egyre önállóbb lesz, egy kulcskérdés merül fel minden kérésnél: **melyik „ész" adja a
választ** — a helyben tanult agy, a lokális Ollama (kulcs nélkül), vagy a felhő-fallback? Ezt egy
kis döntéshozó, az **„arbiter"** intézi, és a `/brain` oldal átláthatóvá teszi, mit miért választott.
A logika a **bizalomra** és az **elérhetőségre** épül:

1. **Tényszerű, memóriában lévő kérdés → helyi agy.** Ha a kérdés kulcsszavai erősen átfednek egy
   tárolt ténnyel/dokumentum-részlettel (magas retrieval-pontszám a fordított indexen), az arbiter a
   **helyi agyat** választja: a megtalált tényből + a Stage 5 sablonokból (vagy a Stage 6 hálóból)
   fogalmaz választ — **külső modell és kulcs nélkül**. Ez a leggyorsabb és legolcsóbb út, és pont
   itt a legmegbízhatóbb a helyi agy, mert a tény a memóriából jön (nem találgat).
2. **Nyitott, általános kérdés, de a PC megy → lokális Ollama.** Ha a kérdés nyitott (nincs rá
   tárolt tény) és a géped fut, az arbiter a **lokális modellt** hívja — szintén kulcs nélkül, csak a
   te géped számol. A memória ekkor is mellé kerül kontextusként, így személyre szabott marad.
3. **Se helyi tény, se futó PC → fallback (Groq/Gemini).** Csak végső esetben fordulunk a felhőhöz,
   és csak ha a felhasználó engedélyezte (kulcs beállítva). Ez **kényelmi opció, nem feltétel**.
4. **Bizonytalanság → őszinteség, nem hallucináció.** Ha egyik forrás sem ad megbízható választ, az
   arbiter inkább **bevallja** (a persona „Honesty" szabálya szerint), vagy egy rövid pontosító
   kérdést tesz fel — sosem talál ki tényt.

A `/brain` „Autonómia-mérő" panelje (Függelék G/6) ezt élőben mutatja: az utóbbi válaszok hány %-a
jött a helyi agytól vs. a lokális modelltől vs. a fallbacktől. A **cél**, hogy idővel — ahogy nő a
memória és a helyi tudás — a helyi arány emelkedjen, a fallback pedig egyre ritkábban kelljen. Így
**méri magát az autonómia**: nem szlogen, hanem egy szám, amit látsz növekedni.

A bizalmi küszöbök (mikortól „elég jó" a helyi válasz) a `/brain` vezérlőpultján hangolhatók: ha
inkább a függetlenséget szereted, lejjebb veszed a küszöböt (többször felel a helyi agy, néha
gyengébben); ha a minőséget, feljebb (kétes esetben a modellhez fordul). Te döntöd el, hol a
kompromisszum — az agy a tiéd, az irányítás is.

---

## Függelék J — GYIK a literal agyról

**Tényleg tud majd kulcs nélkül válaszolni?**
Részben már most: a **lokális Ollamával** (Stage 1) az asszisztens külső kulcs nélkül felel — az „ész"
a te géped. A **nulláról, magától tanult** rész (Stage 2–6) fokozatosan jön, és a tényszerű,
rólad/dokumentumaidról szóló kérdésekre tud majd helyben, kulcs nélkül válaszolni; az általános
folyékonysághoz egy ideig még jól jön a lokális modell.

**Mennyi idő, mire „okos" lesz a nulláról tanult agy?**
Ez a korpuszodtól függ — minél többet beszélgettek és töltesz fel, annál gyorsabban. A `/brain`
„érettségi" sávja őszintén mutatja, hol tart, és mi kell a következő szinthez. Nincs varázslat: az
első napokban naiv, idővel a te témáidban egyre erősebb.

**Olyan okos lesz, mint a ChatGPT?**
Őszintén: nem, nem nulláról egy böngészőben. A nagy modellek hatalmas adaton és GPU-kon tanultak. A
helyi agy a **te szókincsedben/témáidban** lesz hasznos, és a memóriával együtt meglepően jól kezeli
a rólad/dokumentumaidról szóló kérdéseket. A hibrid (helyi tudás + opcionális lokális modell) hozza a
gyakorlati erőt.

**A tanuláshoz az adataim elmennek valahova?**
Nem. A Stage 2–6 tanulás **helyben** történik (a böngésződben/gépeden), külső hívás nélkül. Csak akkor
megy adat külső API-hoz, ha kifejezetten a fallback modellt (Groq/Gemini) használod egy nyitott
kérdésre — és ezt az arbiter + a `/brain` átláthatóan jelzi.

**Átvihetem az agyat másik gépre?**
Igen: az egész agy-állapot (gráf, szókincs, súlyok, profil, emlékek) exportálható egyetlen JSON-ba a
`/brain` vezérlőpultjáról, és máshol visszatölthető. Belépve a Supabase amúgy is szinkronizál az
eszközeid közt.

**Mi van, ha rosszat tanul?**
Mindent láthatsz és javíthatsz a `/brain`-en és a Memória-nézetben: törölhetsz fogalmat/tényt,
csökkentheted a felejtés-rátát, vagy „új agyat" indíthatsz. A megerősítés/felejtés mechanizmus a
hasznosat erősíti, a zajt halványítja.

**Miért éri ez meg a sok külön szakaszt?**
Mert mindegyik **önmagában is működő érték** (pl. az M1 `/brain` oldal már a mai memóriából
látványos), és együtt egy olyan asszisztenst adnak, amely **egyre kevésbé függ bárkitől** — a te
gépeden, a te adataidból, átláthatóan. Ez a „literal agy" reális, lépésenként szállítható útja.

**Mi a legelső lépés, ha belevágunk?**
Az **M1 — `/brain` oldal**: a meglévő memóriából felépített élő asszociációs gráf + statisztikák +
forrás-átláthatóság. Azonnali „belenézek az agyba" élmény, külső kulcs és kockázat nélkül — és erre
épül rá szakaszról szakaszra a többi (szókincs-tanulás, helyi generálás, felejtés/konszolidáció, majd
a helyi háló).

---
---

# III. RÉSZ — A 3D NEURÁLIS AGYTÉRKÉP (a `/brain` oldal teljes vizuális specifikációja)

> Ez a rész a `/brain` oldal **látványának és viselkedésének** részletes terve: egy élő, 3D
> **neurális AI-térkép**, amely úgy néz ki, mint a referenciaképek — egy izzó, részecskékből és
> színes idegszálakból (fiber tracts) álló agy, sötét háttér előtt. Az oldalon **semmi más nincs**,
> csak fent balra az **AuriGPT** felirat és egy **hamburger ikon** (vissza a főoldalra). A térkép
> **maga a memóriád**: minden csomópont egy fogalom/emlék, minden szál egy valódi kapcsolat — és
> amikor új memóriát adsz az agyhoz, az **neuro-szálként nő be**, oda kapcsolódva, ahová tartozik.
> A cél: ne dekoráció legyen, hanem **funkcionális vizualizáció**, ahol minden pixel adatot jelent.

---

## 27. A látvány célja és a referencia

A referenciaképek (az izzó, többszínű agy a kék köddel, és a sötét hátterű, narancs-kék idegháló)
megadják a hangulatot: egy **élő elme térképe**, ahol a sűrű mag a leggyakrabban használt tudás, a
kifelé szétágazó, finom szálak pedig a ritkább, frissebb vagy specifikusabb kapcsolatok. Ez nem
művészi háttér, hanem **a te memóriád 3D-s leképezése** — pont ezért lesz minden eleme jelentéssel
bíró. A `/brain` oldal egyetlen feladata: ezt a térképet a lehető legtisztábban, leglátványosabban és
leginformatívabban megmutatni, minden zavaró elem nélkül.

Három alapelv vezérli a tervet:

- **Minden szál számít.** Nincs díszítő vonal. Minden szál egy valódi asszociáció (két fogalom közti
  kapcsolat) vagy egy memória útja a régiójához. A vastagság, a szín, az átlátszóság és az áramlás
  mind adatot kódol — ha egy szálat látsz, az **jelent valamit**.
- **A térkép a memória.** Nem külön nézet egy lista mellett: maga a 3D agy a memória megjelenítése.
  Egy csomópontra nézve látod, mit tud az agy; egy szálat követve látod, hogyan kapcsolódnak a
  dolgok.
- **Minimalizmus a kereten.** Az oldalon a 3D vászon teljes képernyős; a chrome a minimumra szorítva:
  csak az **AuriGPT** felirat és a **hamburger** fent balra. Semmi más nem versenyez a figyelemért.

---

## 28. Az oldal felépítése — radikális minimalizmus

A `/brain` oldal elrendezése szándékosan szinte üres a 3D-n kívül:

- **Teljes képernyős 3D vászon (canvas).** A teljes viewportot kitölti, sötét (közel fekete / mély
  kékesszürke) háttérrel, finom mélységi köddel. Ez a főszereplő.
- **Fent balra: AuriGPT felirat + hamburger ikon.** Pontosan a meglévő fejléc-stílusban (a
  képernyőképen látható `◈ AURIGPT` + `☰`). A **hamburger ikon visszavisz a főoldalra** (a chatre) —
  ez az egyetlen kötelező navigáció. Az AuriGPT felirat lehet szintén kattintható (vissza a főoldalra).
- **Semmi más állandó UI.** Nincs oldalsáv, nincs alsó sáv, nincsenek panelek, amik eltakarnák az
  agyat. A térkép „lélegzik" a teljes képernyőn.
- **Lebegő, ideiglenes overlay-ek (csak interakcióra).** Amikor egy csomópontra viszed/kattintasz,
  egy **kicsi, áttetsző tooltip/kártya** jelenik meg a kurzor mellett a fogalom adataival (név, súly,
  típus, forrás) — majd eltűnik, ha elhúzol. Ez nem állandó panel, csak kontextuális buborék.
- **Opcionális, elrejtett memória-lista.** Mivel kérted, hogy a memóriák **megjelenjenek** itt is, a
  hamburger (vagy egy apró, sarokban lévő kis fül) lenyithat egy **vékony, áttetsző memória-listát** a
  szél felől, ami szinkronban van a térképpel (egy elemre kattintva a 3D agy odarepül és kiemeli az
  adott csomópontot). De alapból ez is **be van csukva**, hogy a látvány tiszta maradjon — a memóriák
  elsődleges megjelenítése maga a 3D térkép.

A lényeg: amikor megnyitod a `/brain`-t, **az agyat látod, semmi mást** — és minden, amit teszel
(hover, kattintás, keresés), közvetlenül a térképen történik.

---

## 29. A vizuális nyelv (a térkép „grafikai szótára")

Hogy a térkép olvasható és gyönyörű is legyen, egységes vizuális nyelvet használunk — minden vizuális
tulajdonság egy adat-dimenziót kódol:

- **Háttér:** mély, sötét tónus (a HUD-éhoz illő kékesfekete), enyhe vinyetta és mélységi köd, hogy a
  távoli szálak finoman elhalványuljanak — ez adja a térbeli mélységet.
- **Csomópontok (a „neuronok"):** apró, izzó pontok/gömböcskék. **Méret** = a fogalom súlya
  (gyakoriság/fontosság); **fényerő/izzás** = frissesség (a most tanult fogalmak ragyognak, a régiek
  tompábbak); **szín** = típus és régió (lásd lent).
- **Szálak (az „axonok/szinapszisok"):** ívelt, izzó vonalak/csövek a kapcsolódó csomópontok közt.
  **Vastagság** = a kapcsolat erőssége (hányszor fordultak elő együtt); **átlátszóság** = relevancia/
  frissesség; **áramló fény** (kis fénypöttyök futnak végig a szálon) = aktivitás iránya (Markov:
  honnan hová). A szín a két végpont típusából/régiójából keveredik.
- **Részecske-felhő:** a sűrű magban és a szálak mentén finom részecske-permet (a referenciakép
  „porszerű" izzása), ami a tudás sűrűségét és az élő, „lélegző" hatást adja.
- **Bloom/glow:** utófeldolgozott ragyogás a fényes csomópontokon és szálakon — ettől lesz „neonos",
  élő elme-hatása, nem pedig lapos gráf.

A **színkulcs** (típus szerint), hogy ránézésre tudd, mit látsz:
- **Cián/kék** — kulcsszavak és általános fogalmak (a térkép alaphálója).
- **Arany/sárga** — frissen tanult elemek és aktív szinapszisok (a tanulás színe).
- **Meleg piros/narancs** — a sűrű, nagy súlyú mag (a leggyakoribb, legfontosabb tudás), ahogy a
  referenciaképen.
- **Zöld** — dokumentumokból (`doc`/`summary`) származó tudás, hogy elkülönüljön a beszélgetésből
  tanulttól.
- **Fehér/világos mag** — a „rólad" központi csomó (a profil), amely köré az egész szerveződik.

---

## 30. Az adat → 3D leképezés (hogyan lesz a memóriából agy)

Ez a terv magja: pontosan **hogyan** alakul a memória-adat 3D agytérképpé.

### 30.1 Csomópontok (neuronok)

Minden megjelenített csomópont egy valódi memória-elem vagy fogalom:
- a **kulcsszó-emlékek** (`keyword`) a fogalmi háló alap-csomópontjai;
- a **tények** (`fact`) és **összefoglalók** (`summary`) nagyobb, jelölt csomópontok (mert
  konkrét tudást hordoznak);
- a **dokumentum-darabok** (`doc`) zöld csomópontok, a forrás-fájl szerint kötegelve;
- a **profil** (név, érdeklődés) a központi, világos mag-csomópont.

A csomópont attribútumai közvetlenül az adatból jönnek: a `weight` adja a méretet, a `created_at`
frissessége a fényt, a `kind`/régió a színt, a `pinned` pedig egy kis „mag-gyűrűt" vagy extra ragyogást
(a rögzített, mindig fontos tudás kiemelve).

### 30.2 Szálak (axonok / szinapszisok) — és miért fontos mindegyik

A szálak a **II. részben leírt asszociációs gráf** élei: két fogalom közötti együtt-előfordulás. A te
kérésed — „minden szálnak fontosnak kell lennie" — itt **alapelvvé** válik:

- **Nincs díszszál.** Minden megjelenített él egy valódi kapcsolat a memóriában. Ha nincs mögötte
  adat, nincs szál.
- **A szál „beszél":** a vastagsága az élsúly (erős vs. gyenge kapcsolat), a színe a végpontok
  típusa, az áramló fénye az irány és az aktivitás. Egy szálat követve **érted, miért kapcsolódik**
  két fogalom (és kattintásra megnézheted, mely beszélgetésből/dokumentumból ered a kapcsolat).
- **Ritkítás úgy, hogy minden szál megmaradjon jelentősnek.** Ha túl sok az él (sűrű agynál), nem
  random dobunk el, hanem **fontosság szerint** mutatunk: a leg-erősebb és a leg-frissebb szálak
  mindig láthatók, a leghalványabbak a köd/zoom szintjén tűnnek elő. Így a „minden szál fontos" elv
  teljesül: amit látsz, az mindig a jelentős kapcsolat — és közelebb hajolva (zoom) feltárulnak a
  finomabbak is.

### 30.3 Régiók (agyterületek / lebenyek)

A térbeli elrendezés nem véletlenszerű: a fogalmak **témák szerint csoportosulnak**, mint az agy
lebenyei. A II. rész klaszter-detektálása (sűrűn összekötött fogalom-csoportok) adja a régiókat
(pl. „munka/CliMarkAI", „programozás", „család", „nyelvek"). Minden régió:
- a térben **külön zónát** kap (a force-directed elrendezés a klasztereket szétlöki, az éleik
  összehúzzák);
- egy **árnyalatot/színcsaládot** kap, hogy ránézésre elkülönüljön;
- finom, alig látható **buroknal/halo**-val keretezhető, hogy „agyterületként" olvasódjon.

Így a térkép nemcsak szép, hanem **navigálható tudástérkép**: látod, mely témákban „nagy" az agyad,
és melyek a perifériás, frissen formálódó területek.

### 30.4 A „rólad" mag

A térkép közepén a **profilod** áll, mint az identitás magja (név, nyelv, érdeklődés). Minden tudás
ehhez képest helyezkedik el — a hozzád közvetlenül kötődő tények közel, a tágabb fogalmak kifelé. Ez
adja a „ez az ÉN agyam rólam" érzést, és vizuálisan is megmagyarázza, miért személyre szabott minden.

---

## 31. Új memória hozzáadása → neuro-szál animáció („ahova tartozik")

Ez a kért élmény szíve: **amikor pluszt adsz az agyhoz, az neuro-szálként jelenjen meg, oda kötve,
ahová tartozik.** A folyamat lépésről lépésre (akár chatből, akár fájlból, akár kézi hozzáadásból
jön az új memória):

1. **Megszületik a csomópont.** Az új memória (tény/kulcsszó/doc/summary) egy új csomópontként
   felpattan a térkép szélén, halványan, „még nem beágyazott" állapotban.
2. **Az agy megkeresi, hová tartozik.** A háttérben a relevancia-logika (kulcsszó-átfedés a meglévő
   fogalmakkal / a fordított index) **kiszámolja, mely régióhoz és mely meglévő csomópontokhoz
   kapcsolódik** a legjobban — pontosan az a mechanizmus, ami a válaszadáskor is keres.
3. **A szálak „kinőnek".** A kapcsolódó régió(k)ból és hub-csomópontokból **animált idegszálak nőnek
   ki** az új csomópont felé — mint amikor egy neuron axonokat ereszt —, és **rákapcsolódnak**. A
   szálak az erősségük szerint vastagodnak, és arany **szinapszis-villanás** fut végig rajtuk a
   kapcsolódás pillanatában.
4. **Az új csomópont a helyére úszik.** A force-directed elrendezés finoman behúzza az új csomópontot
   a megfelelő régióba (a kapcsolatai „odahúzzák"), így **vizuálisan is látod, hova tartozik** — nem
   a semmiben lóg, hanem beépül a megfelelő agyterületbe.
5. **A régió felragyog.** Az érintett agyterület egy pillanatra felizzik (a tudás „ott nőtt"), és egy
   diszkrét felirat villanhat: „új emlék beépítve → {régió}". Utána a térkép visszatér a nyugodt,
   lélegző alapállapotba, már gazdagabban.

Dokumentum feltöltésekor ez **kötegelt**: a fájl darabjai (`doc` csomópontok) egyszerre nőnek be,
közös zöld „kötegként", a fájlnévhez kötve, a tartalmuk alapján a megfelelő régió(k)hoz húzódva — így
látványosan megjelenik, hogy „ez a dokumentum ezeket a területeket gazdagította".

Ez az animáció nem öncélú: **megmutatja a beágyazás logikáját** — azt, hogy az agy hogyan helyezi el
az új tudást a meglévő szövetében. Pontosan ettől lesz „élő elme" érzés, és pontosan ez a „neuro-szál,
ami megmutatja, hova tartozik", amit kértél.

---

## 32. A memóriák megjelenítése a `/brain` oldalon

Bár a 3D térkép **maga** a memória-megjelenítés, többféleképp is hozzáférhetsz az emlékekhez itt:

- **Közvetlenül a térképen:** minden csomópont egy emlék/fogalom; hover → tooltip az adataival;
  kattintás → kis lebegő kártya a teljes tartalommal, a típussal, a súllyal, a forrással
  (melyik beszélgetés/dokumentum), és gyors műveletekkel (rögzítés, törlés) — ugyanazok a műveletek,
  mint a Memória-nézetben, csak a térképen.
- **Régió-fókusz:** egy régióra kattintva a kamera odarepül, a többi elhalványul, és a régió
  fogalmai/emlékei kiemelve, olvashatóan jelennek meg — így „belenézel" egy témába.
- **Opcionális lista-fül:** a hamburgerből (vagy egy apró sarok-fülből) lenyitható egy vékony,
  áttetsző lista a memóriákról (szűrhető típusra: tény/kulcsszó/dokumentum). Egy elemre kattintva a
  térkép **odarepül és kiemeli** a megfelelő csomópontot + a szálait. Ez a „klasszikus lista" és a
  „3D térkép" összekötése — de alapból be van csukva, hogy a látvány tiszta maradjon.
- **Keresés:** egy minimál kereső (megjelenhet a hamburger-menüben) a beírt szóhoz tartozó
  csomópontokat **felragyogtatja** a térképen, a többit elhalványítja — vizuális „hol van ez a
  tudásomban" kereső.

Így teljesül a kérésed: a memóriák **megjelennek** a `/brain`-en — méghozzá a leggazdagabb formában,
térbeli kontextusban, ahol látod a kapcsolataikat is, nemcsak egy lapos listát.

---

## 33. Render-architektúra (hogyan építjük meg, realisztikusan)

A 3D-hez a React/Vite appban a kézenfekvő, kipróbált eszköz a **Three.js**, lehetőleg a
**react-three-fiber** (R3F) absztrakcióval, ami a Three-t React-komponensként kezeli — így illeszkedik
a meglévő kódhoz. A fő építőelemek:

- **Csomópontok instancinggal.** Több ezer pont/gömb hatékony rajzolásához **instanced rendering**
  (egyetlen draw call sok példányra) vagy egy **Points** rendszer izzó sprite-okkal. Az attribútumokat
  (pozíció, méret, szín, fény) bufferekben adjuk át — így 5–20 ezer csomópont is mehet 60 fps-en.
- **Szálak tube/line geometriával.** Az élek ívelt **görbék** (QuadraticBezier/Catmull-Rom), vékony
  csöveken vagy izzó vonalakon renderelve; az „áramló fény" egy a görbe mentén mozgó UV-eltolás vagy
  apró sprite-ok. A szálak száma a kritikus teljesítmény-tényező → fontosság szerinti ritkítás (lásd 35).
- **Részecskék.** A „por" egy nagy **Points**-rendszer, lassan kavarogva (shaderben animálva), a mag
  körül sűrűbben.
- **Bloom/utófeldolgozás.** Egy **UnrealBloomPass** (vagy hasonló) adja a neonos ragyogást; a köd a
  Three beépített `fog`-jával.
- **Kamera + vezérlés.** OrbitControls-szerű forgatás/zoom/pan; finom auto-rotáció nyugalmi állapotban
  (lassú, mint egy lélegző elme).
- **Layout web workerben.** A 3D force-directed elrendezést (ami CPU-igényes) egy **web worker**
  számolja, hogy a fő szál (a render + UI) sima maradjon; a worker a frissített pozíciókat küldi vissza,
  a render csak interpolál.

Ez mind kliensoldali, kulcs nélküli, a meglévő adatból — nincs hozzá szerver vagy külső szolgáltatás.

---

## 34. Az elrendezés algoritmusa (a 3D forma)

Hogy a térkép **agy alakú** és stabil legyen, nem hagyatkozunk puszta véletlenre:

- **3D force-directed mag.** A csomópontokat egy erő-szimuláció helyezi el: az élek vonzanak (a
  kapcsolódó fogalmak közel kerülnek), a csomópontok taszítják egymást (ne csússzanak össze), egy
  enyhe középre-húzás pedig kompakttá teszi a magot.
- **Régió-szegregáció.** A klaszterekhez extra erő tartozik: az azonos régióba tartozók egymáshoz
  húzódnak, a régiók egymástól ellökődnek → kirajzolódnak az „agyterületek".
- **Agy-sziluett burok (opcionális, de látványos).** A pontfelhőt egy **agy-alak térfogatába**
  szoríthatjuk (egy egyszerű agy-mesh vagy implicit forma „envelope"-jaként), hogy a referenciakép
  agy-formája adódjon — a sűrű mag belül, a finom szálak kifelé ágazva.
- **Determinisztikus seed.** Az elrendezés egy rögzített kezdő-magból indul, hogy **stabil** legyen:
  ne ugráljon teljesen újra minden betöltéskor — a már megszokott „tájékozódási pontjaid" a helyükön
  maradnak, az új tudás közéjük épül.
- **Inkrementális frissítés.** Új memóriánál nem rendezünk újra mindent: csak az új csomópontot és a
  szomszédait engedjük „beülni" (lokális relaxáció), a többi marad — ez adja a 31. szakaszbeli
  „beépül a helyére" animációt, és tartja a stabilitást.

---

## 35. Teljesítmény és skálázódás

Egy nagy, élő 3D agy a teljesítmény miatt a legkockázatosabb rész — ezért tudatosan tervezzük:

- **Instancing + bufferek** a csomópontokhoz (egy draw call), nem külön mesh-ek.
- **Szint-alapú részletesség (LOD).** Távolról csak a nagy, fontos csomópontok és erős szálak; közelebb
  hajolva (zoom) tárulnak fel a finomabbak. Így „minden szál fontos" marad, de nem terheljük túl a GPU-t
  egyszerre.
- **Fontosság-alapú ritkítás.** Ha túl sok az elem, a legkisebb súlyú/leghalványabb szálakat csak a
  megfelelő zoom-szinten rajzoljuk — sosem random, mindig fontosság szerint.
- **Frustum culling + a worker-layout**, hogy a fő szál szabad maradjon.
- **Cél: 60 fps** modern gépen, és kecses visszaesés gyengébb gépen (kevesebb részecske, halványabb
  bloom). Mobilon egy egyszerűsített mód.
- **Big-O tudatosság.** A render a *látható* elemekkel skálázódik (LOD/cull miatt), nem a teljes
  memóriával; a layout inkrementális. Így több ezer emléknél is élvezhető marad.

---

## 36. Adatfolyam és állapot

A `/brain` egy új `useBrainGraph` hookból táplálkozik, amely a meglévő `useMemory`/`memStore` adataiból
építi a gráfot (a II. rész co-occurrence logikájával) és feliratkozik a változásokra:

- **Betöltés:** a memóriákból felépül a csomópont- és élhalmaz + a klaszterek; a layout-worker kiszámolja
  a kezdő pozíciókat.
- **Élő frissítés:** amikor a fő chaten új memória keletkezik (vagy fájlt töltesz fel), a hook észleli,
  hozzáadja az új csomópontot/éleket, és kiváltja a 31. szakaszbeli beépülő animációt — akár ha közben
  a `/brain` oldalon vagy, akár ha visszatérsz rá.
- **Perzisztált agy-állapot:** a layout-seed, a régió-hozzárendelés és a nézet-beállítások egy
  `brain_state` rekordban (Supabase belépve, localStorage vendégként), hogy a térképed **stabil és
  hordozható** legyen a látogatások közt.

Minden adat per-felhasználó és izolált (RLS / a saját böngésződ) — a `/brain` semmi újat nem tesz
ki kifelé, csak vizualizálja, ami már a tiéd.

---

## 37. Hozzáférhetőség és visszafogott mód

- **`prefers-reduced-motion`:** ha a rendszered kéri, az auto-rotáció, az áramló fények és a
  szinapszis-villanások visszafogottak vagy statikusak lesznek — a térkép akkor is teljes értékű,
  csak nem mozog folyamatosan.
- **2D tartalék.** Gyenge GPU-n vagy WebGL hiányában egy egyszerűbb **2D gráf-nézet** ugorhat be
  (ugyanaz az adat, könnyebb render), hogy a `/brain` mindig elérhető legyen.
- **Billentyűzet + tooltip.** A csomópontok között lehessen lépkedni, a tooltipek olvashatók, a
  kontraszt elég magas (a sötét háttér + világos szöveg segít).
- **Teljesítmény-kapcsoló.** A felhasználó visszavehet a részecskeszámból/bloomból, ha a gépe gyenge.

---

## 38. Bekötés és routing (hogyan lesz külön oldal)

- **`/brain` útvonal.** A Vite/React appba egy könnyű útválasztás (vagy egy `view` állapot) vezeti be a
  `/brain` nézetet a fő chat mellé. A főoldalról a **BRAIN-cardról** és/vagy egy fejléc-gombról lehet
  ide jutni.
- **A hamburger visszavisz.** A `/brain` fent balra csak az **AuriGPT** feliratot és a **hamburger
  ikont** mutatja; a hamburger (és/vagy a felirat) **vissza a főoldalra** (a chatre). Más állandó UI
  nincs.
- **Külön mountolt 3D.** A nehéz 3D komponens csak akkor töltődik be (lazy import), amikor a `/brain`-re
  lépsz — így a fő chat gyors marad, és a 3D nem terheli, amíg nem nézed.
- **Nincs ütközés.** A `/brain` saját, új komponensekből áll (`useBrainGraph`, a 3D nézet, a tooltip),
  és a meglévő memória-adatra épül — így megépíthető anélkül, hogy a fő chat- vagy reszponzivitás-kódba
  bele kéne nyúlni.

---

## 39. Implementációs lépések (a 3D `/brain` lebontva)

Hogy ne egyszerre kelljen az egészet megépíteni, fokozatosan szállítható:

1. **B1 — Váz + minimál chrome.** A `/brain` route, teljes képernyős vászon, fent balra AuriGPT +
   hamburger (vissza). Üres 3D jelenet, háttér, kamera, kontroll.
2. **B2 — Csomópontok a memóriából.** A `useBrainGraph` felépíti a csomópontokat; instanced pontok,
   méret/szín/fény az adatból; hover-tooltip.
3. **B3 — Szálak.** Az asszociációs élek megrajzolása (íves szálak), vastagság/szín az adatból; LOD +
   fontosság-ritkítás.
4. **B4 — Régiók + layout.** Klaszterezés, 3D force-directed elrendezés a workerben, régió-színek,
   a „rólad" mag középen.
5. **B5 — Bloom + részecskék + élet.** Utófeldolgozott ragyogás, részecske-permet, lassú lélegzés/
   auto-rotáció.
6. **B6 — Beépülő animáció.** Az új memória → szál-kinövés + szinapszis-villanás + a régió felizzása
   (a 31. szakasz).
7. **B7 — Interakció teljes.** Kattintás-kártya (forrással, műveletekkel), régió-fókusz (fly-to),
   keresés-kiemelés, opcionális lista-fül.
8. **B8 — Csiszolás.** Teljesítmény (LOD, ritkítás, mobil), `prefers-reduced-motion`, 2D tartalék,
   perzisztált `brain_state`.

Már a **B1–B3** is ad egy igazi „3D neurális térkép a memóriámból" élményt; a többi réteg fokozatosan
teszi élővé és látványossá.

---

## 40. Kockázatok és őszinte korlátok (3D)

- **Teljesítmény a fő kockázat.** Sok ezer szál 3D-ben nehéz; ezért a LOD + fontosság-ritkítás + worker
  nem opció, hanem szükséglet. Gyenge gépen a 2D tartalék biztosítja, hogy mindig működjön.
- **Olvashatóság vs. „minden szál".** Ha tényleg minden szálat egyszerre mutatnánk nagy agynál, az
  „szőrgombóc" lenne. A megoldás: minden szál **létezik és elérhető**, de a megjelenítés zoom/fontosság-
  vezérelt — közelebb hajolva tárul fel a részlet. Így a „minden szál fontos" elv **igaz** marad
  (nincs álszál), de a kép olvasható.
- **Mobil.** A teljes 3D + bloom mobilon nehéz; ott egyszerűsített mód (kevesebb elem, kisebb bloom)
  vagy a 2D nézet a reális.
- **Ez vizualizáció, nem maga az intelligencia.** A 3D térkép a memória/asszociációk **megjelenítése** —
  gyönyörű és informatív, de a tanulást (II. rész) a motor végzi; a térkép az ablak rá, nem a motor.

---

## 41. Záró — a látvány mint funkció

A `/brain` oldal célja, hogy amikor megnyitod, **belenézz a saját AI-agyadba**: egy élő, 3D neurális
térképbe, ahol a sűrű, meleg mag a legfontosabb tudásod, a kifelé ágazó, izzó szálak a kapcsolatok, a
színes régiók a témáid, a középső világos mag pedig te magad. Az oldalon semmi más nem zavar — csak
fent az **AuriGPT** felirat és a **hamburger**, amivel visszamész. A memóriák itt nem listaként, hanem
**térbeli, összekötött szövetként** jelennek meg, és amikor új tudást adsz az agynak, **látod, ahogy
egy neuro-szál kinő és a helyére kapcsolódik** — pontosan oda, ahová tartozik.

Ez egyszerre **élmény** (egy lenyűgöző, J.A.R.V.I.S.-szerű elme-szkenner) és **funkció** (minden szál
valódi adat, minden csomópont egy emlék, minden animáció a beépülés logikáját mutatja). Nagy és
bonyolult — ezért építjük rétegekben (B1–B8), kliensoldalon, a meglévő memóriából, kulcs nélkül, a
saját fájljainkban. A végeredmény: az agy, amit elképzeltél — **láthatóan, kézzelfoghatóan, a tiéd**.

---

## Függelék K — A 3D agytérkép adatszerkezetei (pszeudokód)

Hogy a `/brain` 3D nézet megépíthető legyen, ezek a központi szerkezetek (a meglévő memóriából
származtatva, a `useBrainGraph` hookban):

```
BrainNode {
  id            // a memória/fogalom azonosítója
  label         // a megjelenített szöveg (szó, tény rövidítve)
  kind          // 'profile' | 'fact' | 'keyword' | 'doc' | 'summary'
  weight        // súly → csomópont-méret
  freshness     // created_at alapján → izzás/fény
  pinned        // rögzített → mag-gyűrű / extra ragyogás
  regionId      // melyik klaszterhez/agyterülethez tartozik
  sources       // honnan tanulta (conv/doc id-k) → forrás-átláthatóság
  pos: {x,y,z}  // a layout-worker által számolt pozíció
  color         // a kind + regionId alapján
}

BrainEdge {
  a, b          // a két csomópont id-je
  strength      // együtt-előfordulás súlya → szál-vastagság
  dir           // irány (Markov A→B vs B→A) → áramló fény iránya
  fresh         // frissesség → átlátszóság/izzás
}

BrainRegion {
  id            // klaszter azonosító
  label         // a téma neve (a leggyakoribb kulcsszó a klaszterben)
  hue           // a régió színcsaládja
  centroid      // a régió térbeli középpontja
  nodeIds       // a benne lévő csomópontok
}

BrainLayoutState {
  seed          // determinisztikus kezdő-mag (stabil elrendezés)
  positions     // node id → {x,y,z} (a worker frissíti)
  envelope      // opcionális agy-sziluett burok paraméterei
}
```

A `useBrainGraph` ezeket a meglévő `memories` tömbből építi: a csomópontok az emlékek/fogalmak, az
élek a kulcsszó-átfedésekből (a II. rész fordított indexe), a régiók a klaszterezésből. Új memóriánál
egy `BrainNode` és a hozzá tartozó `BrainEdge`-ek keletkeznek, és a layout-worker **lokálisan**
relaxálja a környezetüket (nem rendez újra mindent), ez adja a 31. szakaszbeli beépülő animációt.

---

## Függelék L — Vizuális → adat leképezés (a teljes „szótár")

Minden vizuális tulajdonság egy adat-dimenziót kódol — semmi sem dekoráció:

| Vizuális elem | Tulajdonság | Mit kódol (adat) |
|---|---|---|
| Csomópont | méret | `weight` (fontosság/gyakoriság) |
| Csomópont | fényerő/izzás | frissesség (`created_at`) |
| Csomópont | szín | `kind` + régió (típus és téma) |
| Csomópont | mag-gyűrű / extra glow | `pinned` (rögzített tudás) |
| Csomópont | központi, világos | `profile` (a „rólad" mag) |
| Szál | vastagság | `strength` (kapcsolat erőssége) |
| Szál | szín | a két végpont típusa/régiója (kevert) |
| Szál | áramló fénypöttyök | `dir` (Markov-irány, aktivitás) |
| Szál | átlátszóság | frissesség/relevancia |
| Régió | színcsalád (hue) | a téma (klaszter) |
| Régió | térbeli zóna + halo | az agyterület elkülönülése |
| Részecske-sűrűség | a mag körül | a tudás sűrűsége (mennyit tud ott) |
| Szinapszis-villanás (arany) | egyszeri | épp most tanult/kapcsolódott |
| Köd / mélységélesség | távolság | térbeli mélység, fókusz |

Ez a táblázat egyben a „minden szál fontos" elv garanciája: ha valami megjelenik a térképen, az a
fenti adatok valamelyikét mutatja — sosem önmagáért való díszítés.

---

## Függelék M — Interakció-forgatókönyvek (lépésről lépésre)

**Hover egy csomópont fölött.** A csomópont kiemelődik (nagyobb glow), a közvetlen szomszédai és a
hozzájuk vezető szálak felragyognak, a többi enyhén elhalványul. Egy kis tooltip jelzi a fogalmat, a
típust, a súlyt és a forrást. Elhúzva minden visszatér.

**Kattintás egy csomópontra.** A kamera finoman ráközelít; egy lebegő kártya megnyílik a teljes
tartalommal (a tény/dokumentum-részlet szövege), a forrással (melyik beszélgetés/fájl, mikor), és
gyors műveletekkel (rögzítés ★, törlés ✕) — ugyanazok, mint a Memória-nézetben, csak térben. A
kártya bezárható; a térkép visszaáll.

**Régió-fókusz.** Egy régió-halóra kattintva a kamera odarepül (fly-to), a többi régió elhalványul és
hátrébb húzódik, a fókuszált téma fogalmai pedig olvashatóan, címkézve jelennek meg. Így „belenézel"
egy agyterületbe. Vissza: dupla kattintás az üres térre vagy egy „vissza" gesztus.

**Keresés.** A (hamburgerből előhúzható) keresőbe gépelve a térkép a találatokat **felragyogtatja**,
a többit elhalványítja, és a kamera a legrelevánsabb találatra úszik. Ez a „hol van ez a tudásomban"
vizuális kereső.

**Új memória érkezik (chatből/fájlból).** A szél felől felpattan az új csomópont; a háttér kiszámolja,
hova tartozik; a kapcsolódó régióból szálak nőnek ki és rákapcsolódnak (arany villanással); a csomópont
a helyére úszik; a régió egy pillanatra felizzik. Ha épp nézed, **látod élőben**; ha visszatérsz,
már beépülve találod.

**Üres állapot (még nincs memória).** A térkép egy halvány, „alvó" magot mutat a profil-csomóval, és
egy diszkrét felirattal bátorít: „Beszélgess vagy tölts fel egy fájlt — és nézd, ahogy az agy nőni
kezd." Az első emlékkel életre kel.

---

## Függelék N — Teljesítmény-költségvetés (számok és szintek)

Hogy a „nagy és bonyolult" ne jelentsen „lassút", konkrét keretek:

- **Cél: 60 fps** modern asztali gépen; **≥ 30 fps** közepesen; mobilon egyszerűsített mód vagy 2D.
- **Csomópont-szintek (LOD):** ~0–500 csomópont: minden látszik, teljes részlet. ~500–3000:
  instancing + a kis súlyúak csak közelebb. 3000 felett: csak a top-súlyú mag + a fókuszált régió
  részletei, a többi köd/aggregátum.
- **Szálak:** alapból csak a fontossági küszöb feletti élek; zoomra/fókuszra tárulnak a finomabbak.
  Cél: egyszerre ~néhány ezer látható szál maximum (a többi létezik, csak nem rajzolt épp).
- **Draw call-ok:** a csomópontok 1 instanced hívásban; a szálak típusonként/kötegként összevonva;
  a részecskék 1 rendszerben. Cél: tartani alacsonyan a draw call-okat.
- **Layout a workerben:** a force-directed iterációk a fő szálon kívül; a render csak interpolál a
  legutóbbi pozíciókhoz → nincs akadás.
- **Lusta betöltés:** a teljes 3D köteg (Three.js) csak a `/brain`-re lépve töltődik, hogy a fő chat
  bundle-je kicsi maradjon.
- **Kecses visszaesés:** gyenge GPU-n kevesebb részecske, halványabb bloom, kevesebb látható szál —
  vagy a 2D gráf-nézet. A `/brain` sosem „törik el", csak egyszerűsödik.

---

## Függelék O — GYIK a 3D `/brain`-ről

**Tényleg úgy fog kinézni, mint a referenciaképek?**
Az a cél: izzó, részecskés mag + színes idegszálak, sötét háttér, neonos bloom. A pontos forma a te
adatodtól függ (a te agyad egyedi), de a *stílus* és a *hangulat* az lesz.

**Miért nincs az oldalon más, csak a logó és a hamburger?**
Mert kérted — és mert így a térkép kapja a teljes figyelmet. A chrome minimalizmusa szándékos: az agy
a főszereplő, a hamburger pedig egyetlen tiszta út vissza a főoldalra.

**Tényleg minden szál fontos?**
Igen: nincs díszszál. Minden szál egy valódi asszociáció vagy egy memória útja a régiójához. Hogy a
kép olvasható maradjon, a megjelenítés zoom/fontosság-vezérelt — de minden szál létezik és elérhető.

**Mi történik, ha új memóriát adok?**
Egy új csomópont jelenik meg, és **neuro-szálak nőnek ki** hozzá a kapcsolódó régióból/fogalmaktól,
megmutatva, hova tartozik — arany szinapszis-villanással, majd a helyére úszik. Pontosan az „élő
beépülés", amit kértél.

**Lassú lesz a gépemen?**
A LOD + ritkítás + worker miatt törekszünk 60 fps-re; gyenge gépen egyszerűsödik (vagy 2D), de mindig
működik. A 3D köteg csak a `/brain`-en töltődik be, így a chat gyors marad.

**Az adataim biztonságban vannak?**
Igen: a `/brain` csak **vizualizálja** a már meglévő, per-felhasználó izolált memóriát (RLS / a saját
böngésződ). Semmi újat nem küld kifelé.

**Megépíthető anélkül, hogy ütköznél a másik AI-jal?**
Igen: a `/brain` saját, új komponensekből áll (`useBrainGraph` + a 3D nézet), és a meglévő
memória-adatra épül — nem kell a fő chat- vagy reszponzivitás-kódhoz nyúlni. Külön route, lusta
betöltés, saját fájlok.

**Mi az első lépés?**
A **B1–B3**: a `/brain` route + minimál chrome (AuriGPT + hamburger), majd a csomópontok és a szálak a
memóriából — már ez ad egy igazi „3D neurális térkép a memóriámból" élményt, amire a többi réteg
(régiók, bloom, beépülő animáció, interakció) ráépül.

---

## Függelék P — Render- és shader-jegyzetek (hogyan lesz „izzó élő agy")

A referenciaképek hangulatát néhány konkrét grafikai technika adja — érdemes előre rögzíteni, hogy a
megvalósítás ne „lapos gráf", hanem **élő, izzó elme** legyen:

- **Additív izzás (additive blending).** A csomópontok és a szálak fénye **összeadódik** ott, ahol
  átfednek — ezért világít fel a sűrű mag erősen (sok átfedő fény), a perifériás szálak pedig finoman.
  Ez adja a referenciakép „belülről világító" hatását.
- **Sprite-alapú neuronok.** A csomópontok nem tömör gömbök, hanem **lágy, izzó pontok** (radiális
  gradiens sprite), amelyek mindig a kamera felé néznek (billboard). Olcsó és gyönyörű — több ezer is
  mehet belőle.
- **Áramló szálak.** A szálakon a „mozgó fény" egy a görbe mentén csúsztatott textúra-UV vagy apró
  fénypöttyök sora; a sebesség és az irány a `dir`/aktivitás. Ettől „élnek" a szinapszisok, mintha
  jel futna rajtuk.
- **Bloom utófeldolgozás.** Egy küszöb feletti fényre rátett **bloom** (elmosott ragyogás) adja a
  neonos hatást; mértékkel, hogy ne mossa el a részleteket. Gyenge gépen visszavehető.
- **Mélységi köd + vinyetta.** A távoli elemek a háttérbe olvadnak (köd), a képszélek finoman
  sötétednek (vinyetta) — így a tekintet a magra fókuszál, és valódi térmélység-érzet keletkezik.
- **Színkeverés a szálakon.** Egy szál a két végpont színe közt **átmenetet** kap (pl. cián kulcsszó →
  zöld dokumentum = cián-zöld átmenet), így ránézésre látod, milyen típusú dolgokat köt össze.
- **Kamera-dramaturgia.** Nyugalomban lassú, alig érezhető **auto-orbit** (mint egy lélegző elme); a
  fly-to mozgások „easing"-gel simulnak; tanuláskor egy apró, finom „kamera-rezdülés" kísérheti a
  szinapszis-villanást (visszafogottan, `prefers-reduced-motion` mellett kikapcsolva).

Mindez a Three.js/react-three-fiber eszköztárából elérhető (sprite-ok, vonal/cső-geometria,
EffectComposer + bloom, fog), és a teljesítmény-budget (Függelék N) keretein belül marad.

---

## Függelék Q — A 3D térkép mint a tanulás tükre (összekötés a II. résszel)

A `/brain` nemcsak „szép gráf" — egyúttal **a II. részben leírt tanulás vizuális tükre**. Így kapcsolódik
a kettő, hogy az oldal a valódi „agy-állapotot" mutassa, ne csak egy pillanatképet:

- **A szakaszok (Stage 0–6) a térkép gazdagságában látszanak.** Stage 0–1-nél a térkép ritka, a mag
  körül kevés szállal; ahogy a szókincs és az asszociációk nőnek (Stage 3–4), a háló **sűrűsödik**, új
  régiók formálódnak. A térkép ránézésre mutatja, „mennyire fejlett" az agyad — ez a 23.1-ben említett
  érettség, csak vizuálisan.
- **Az új szó / új asszociáció tanulása élő esemény.** Amikor a motor új kulcsszót vagy kapcsolatot
  tanul (II. rész), az a `/brain`-en **azonnal** új csomópontként / szálként pattan fel a megfelelő
  régióba — a tanulás nem absztrakció, hanem **látható** történés.
- **A megerősítés és a felejtés a vizuálban.** A gyakran előjövő (megerősített) fogalmak nőnek és
  fényesednek; a régóta irreleváns tudás (decay) halványul és hátrébb húzódik — így a térkép idővel a
  **fontos** tudást emeli ki, a zajt elhalványítja. A konszolidáció („alvás") után a régi részletek
  egy `summary`-csomóba olvadnak — látod, ahogy „letisztul" az agy.
- **Az autonómia-arány a térképen.** A `/brain` jelezheti (pl. a mag színével vagy egy diszkrét
  mutatóval), hogy az utóbbi válaszok mekkora hányada jött a **helyi agytól** (kulcs nélkül) vs. a
  lokális modelltől vs. a fallbacktől — vagyis látod, ahogy az agy egyre inkább „a saját lábán áll",
  ahogy a II. rész szakaszai beérnek.
- **A forrás-átláthatóság összeköti a chattel és a dokumentumokkal.** Bármely csomópontnál látod,
  melyik beszélgetésből vagy fájlból ered — egy kattintással átugorhatsz a forrásra. Így a `/brain`
  nem sziget: a chat táplálja, a dokumentumok gazdagítják, a profil a magja, és minden összeér.

Ez a kapcsolat teszi a `/brain`-t igazán értékessé: nem egy különálló látványosság, hanem **az élő,
tanuló elme műszerfala** — amin keresztül nemcsak gyönyörködsz, hanem **érted és irányítod** is, mit
és hogyan tanul az agyad, miközben szakaszról szakaszra önállóbbá válik.

> **A teljes BRAIN.md most három részből áll:** I. a *mai* memória + kontextus-rendszer; II. a *literal
> agy* víziója és a tanulás szakaszai (betűk → szavak → válaszadás, kulcs nélkül); III. a *3D neurális
> agytérkép* a `/brain` oldalon (minimál chrome, minden szál fontos, élő beépülő animáció). Együtt ez a
> teljes terv: hogyan működik ma, hová tart, és hogyan fogod látni és irányítani — őszintén, reálisan,
> a saját kezedben.

---

## Függelék R — Elfogadási kritériumok a `/brain` oldalhoz

Hogy egyértelmű legyen, mikor „kész" a 3D agytérkép, íme egy ellenőrző lista. Egy elemet se tekints
késznek, amíg a megfelelő pont nem teljesül:

1. ☐ A `/brain` **külön nézet**, a főoldalról (BRAIN-card / fejléc) elérhető; a 3D köteg csak ide lépve
   töltődik be (lusta betöltés), a chat bundle-je nem nő érdemben.
2. ☐ Az oldalon **csak** fent balra az **AuriGPT** felirat és a **hamburger** látszik; a hamburger
   (és a felirat) **visszavisz a főoldalra**. Nincs más állandó UI.
3. ☐ A 3D vászon **teljes képernyős**, sötét háttérrel, mélységi köddel; a meglévő HUD-stílusban
   (cián glow, neonos bloom).
4. ☐ Minden **memória megjelenik** csomópontként; minden **asszociáció szálként** — és **minden szál
   valódi adat** (nincs díszszál). A vizuál → adat leképezés (Függelék L) érvényes.
5. ☐ A csomópontok mérete/színe/fénye az adatból jön (súly, típus/régió, frissesség); a `pinned` és a
   `profile` mag kiemelve.
6. ☐ **Új memória hozzáadásakor** a csomópont felpattan, a kapcsolódó régióból **neuro-szálak nőnek
   ki** hozzá (arany szinapszis-villanással), és a helyére úszik — láthatóan **oda, ahová tartozik**.
7. ☐ **Interakció:** hover-tooltip, kattintás-kártya (forrással + művelettel), régió-fókusz (fly-to),
   keresés-kiemelés. A memóriák innen is kezelhetők (rögzítés/törlés).
8. ☐ **Teljesítmény:** modern gépen ~60 fps a budget szerint (LOD, fontosság-ritkítás, instancing,
   worker-layout); gyenge gépen kecses visszaesés vagy 2D tartalék; `prefers-reduced-motion`-barát.
9. ☐ **Adat + biztonság:** a térkép a meglévő, per-felhasználó izolált memóriából épül (RLS / saját
   böngésző); semmi újat nem küld kifelé; a `brain_state` perzisztált és exportálható.
10. ☐ **Nincs ütközés:** saját, új komponensek (`useBrainGraph` + 3D nézet); a fő chat/reszponzivitás
    kódhoz nem kell nyúlni.

Ha mind a tíz pont zöld, a `/brain` készen áll: egy élő, 3D neurális AI-térkép, ami a memóriádat
mutatja, ahol minden szál számít, és ahol látod, ahogy az agy tanul és beépíti az új tudást — pontosan
úgy, ahogy elképzelted.
