# Fogalomtár

> **Miről szól:** a `thinking/` dokumentumaiban használt fogalmak egy helyen — magyarul, az angol
> megfelelővel (a kódban és az azonosítókban az angol alakot használjuk). Ha új fogalmat vezetsz be
> egy dokumentumban, **ide is vedd fel**.

Jelölés: a „Hol” oszlop a fő részletező fájlra mutat (a `thinking/` mappához képest), rövidítve:
`01-architektura/02` = a mappa `02-…` kezdetű fájlja; `08-modellek…` = `08-modellek-es-utvonalvalasztas`,
`09-biztonsag…` = `09-biztonsag-es-adatvedelem`, `10-meres…` = `10-meres-es-fejlodes`,
`04-nyelv…` = `04-nyelv-es-mondatalkotas`.

## A. A rendszer részei

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **BRAIN** (agy) | `brain` | Auri tanuló agya; ma a böngészőben (`web/src/brain/**`), később az Auri Core-ban | `thinking.md` |
| **Auri Core** | `auri_core` | A helyi szolgáltatás, ahová a BRAIN költözik; az AuriGPT és a Jarvis közösen használja | `01-architektura/03` |
| **AuriGPT** | — | A webes chat-felület (`web/`) | `thinking.md` |
| **Jarvis** | `auri-jarvis` | A helyi, hangos asszisztens-daemon; a „Mind” része már Ollamával gondolkodik | `thinking.md` |
| **Memória / Tudástár** | knowledge store | Az ellenőrzött tudás, kódrészletek, források, epizódok tára (SQLite) | `01-architektura/04` |
| **Kódtudástár** | code knowledge base | Kódrészletek **tesztekkel** együtt, ellenőrzési állapottal | `06-programozas/03` |
| **Router** (útvonalválasztó) | `router` | Eldönti: cache, fast-path, melyik modell, kell-e web vagy felhő | `08-modellek…/02` |
| **Gondolkodók** | thinkers | A helyi modellek a belső szerepekkel (ld. B: Szerepek) és a Fogalmazó | `02-belso-parbeszed/01` |
| **Web-szörföző** | web surfer | Keresés → oldalolvasás → lényegkivonás → bizalom | `03-web-szorfozes/` |
| **Ellenőrző / Sandbox** | verifier / sandbox | Kódot futtat elszigetelten, tényt egyeztet forrásokkal | `06-programozas/04` |
| **Ütemező** | scheduler | Az egyetlen Ollama-sáv kiosztása, elsőbbség, tétlenség, háttérfeladatok | `08-modellek…/02` |
| **Tananyag-kezelő** | curriculum manager | Mit tanuljon, milyen sorrendben, mikor ismételjen | `05-tanulas/02` |
| **Ciklusvezérlő** | loop runner | A gondolkodó ciklus lépéseit futtatja, keretet figyel, epizódot ír | `01-architektura/02` |
| **Adatvédelmi kapu** | privacy gate | Minden írás előtt kiszűri a személyes adatot és a titkot | `09-biztonsag…/01` |

## B. Gondolkodás

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **Gondolkodó ciklus** | thinking loop | Emlékezés → megértés → terv → cselekvés → ellenőrzés → (javítás) → tanulság → megjegyzés | `01-architektura/02` |
| **Epizód** | episode | A ciklus egy lefutásának teljes naplója (cél, lépések, modellek, idő, eredmény) | `01-architektura/04` |
| **Tapasztalat** | experience | Az epizódok összessége, amiből a router és a tananyag tanul | `01-architektura/04` |
| **Tanulság** | lesson | Rövid, szerkezett jegyzet: mi működött, mi nem, miért; később visszakereshető | `01-architektura/02` |
| **Gyors / lassú gondolkodás** | fast / slow path | Gyors: cache + fast-path + ellenőrzött tudás. Lassú: a teljes ciklus modellekkel | `00-alapok/01` |
| **Metakogníció** | metacognition | „Tudom / nem tudom” becslés külső jelekből (lefedettség, sikerarány, frissesség) | `00-alapok/01` |
| **Nehézségbecslés** | difficulty estimate | A router induló szintjét és a keretet meghatározó pontszám | `08-modellek…/02` |
| **Eszkaláció** | escalation | Kudarc után egy szinttel erősebb út (nagyobb modell, web, felhő) | `08-modellek…/02` |
| **Költségkeret** | budget | Max. LLM-hívás, token, falióra-idő, javítási kör, weblekérés egy feladatra | `01-architektura/02` |
| **Javítási kör** | repair round | Hiba után új próbálkozás a hibaüzenettel; legfeljebb 3 | `06-programozas/06` |
| **Belső párbeszéd** | inner dialogue | A szerepek egymásnak írnak (egy sávon, egymás után) | `02-belso-parbeszed/` |
| **Szerepek** | roles | Kérdező, Gondolkodó (Javasló), Tesztelő, Kritikus, Tanár; segéd: Kivonatoló, Választó | `02-belso-parbeszed/01` |
| **Szerepkönyv** | role book | Az egyetlen, bájtra stabil rendszerprompt, ami minden belső szerepet leír; a szerep a felhasználói üzenetben (`<szerep>KRITIKUS</szerep>`) | `02-belso-parbeszed/04` |
| **Persona-munkamenet** | persona session | A felhasználóval folyó beszélgetés (Jarvis / AuriGPT persona-előtaggal) | `02-belso-parbeszed/01` |
| **Fogalmazó** | composer | A felhasználónak szóló válasz megírása a persona-munkamenetben, a belső eredményből | `02-belso-parbeszed/04` |
| **Döntés** | decision (rule-based) | Nem modell: szabályalapú kód dönt a szerepek kimenetéből (zöld teszt? blokkoló kritika? keret?) | `02-belso-parbeszed/02` |
| **Vita-protokoll** | debate protocol | A szerepek rögzített sorrendű, korlátos érvelése | `02-belso-parbeszed/02` |
| **Önkérdezés** | self-questioning | A rendszer saját pontosító kérdései a megértés lépésben | `02-belso-parbeszed/03` |
| **Feladatbontás** | task decomposition | Komplex cél → kisebb, egyenként ellenőrizhető lépések | `07-komplex-feladatok/01` |
| **Terv–végrehajtás–ellenőrzés** | plan–execute–verify | Minden lépésnek előre megadott ellenőrzési pontja van | `07-komplex-feladatok/02` |
| **Önellenőrzés** | self-check | A kész eredmény újraellenőrzése a teljes célra (nem csak lépésenként) | `07-komplex-feladatok/04` |

## C. Modellek és futtatás

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **Helyi modell** | local model | Ollamán futó nyelvi modell (pl. `gemma4:e2b`) | `08-modellek…/01` |
| **Kódolómodell** | coder model | Programozásra hangolt modell; még nincs telepítve | `08-modellek…/01` |
| **Ollama-sáv** | slot (`OLLAMA_NUM_PARALLEL=1`) | Egyszerre egy kérés fut; a többi sorban áll | `00-alapok/03` |
| **Első token** | time to first token (TTFT) | A kérés indulásától az első kimeneti tokenig eltelt idő | `00-alapok/03` |
| **tok/s** | tokens per second | Generálási sebesség | `00-alapok/03` |
| **Prefill** | prefill | A prompt feldolgozása a generálás előtt; CPU-n ez a drága rész | `08-modellek…/01` |
| **KV-cache** | KV cache | A már feldolgozott prompt belső állapota; csak egy korábbi prompt **végéről** folytatható | `08-modellek…/01` |
| **Előtag / prefixváltás** | prefix / prefix switch | A prompt állandó eleje; cseréje új prefillt okoz (mért: ~6 s e2b) | `00-alapok/03` |
| **Hideg betöltés** | cold load | A modell betöltése a memóriába (mért: 18,5–38,3 s) | `00-alapok/03` |
| **Seed-pár** | seed exchange | Rögzített nyitó kérdés–válasz a rendszerprompt után, hogy a cache találjon (Jarvis) | `08-modellek…/01` |
| **Kontextusablak** | context window (`num_ctx`) | Ennyi tokent lát egyszerre a modell | `08-modellek…/01` |
| **Kvantálás** | quantization (Q4, `q8_0`) | Kisebb pontosságú súlyok/cache → kevesebb RAM | `08-modellek…/01` |
| **think / okos mód** | thinking mode | A modell előbb „gondolkodó” tokeneket ír; lassabb, csak háttérben | `08-modellek…/01` |
| **Strukturált kimenet** | structured output | A modell JSON-sémához kötött választ ad (Ollama `format`) | `02-belso-parbeszed/04` |
| **Fast-path** | fast path | Modell nélküli, regex + fuzzy parancsfelismerés (Jarvis: 0,05 ms/mondat) | `08-modellek…/02` |
| **Felhős segítség** | cloud assist | Groq / Gemini, opcionális, alapból kikapcsolva | `08-modellek…/03` |
| **Kvóta / 429** | rate limit / HTTP 429 | A felhőkeret kifogyott; a router továbblép | `08-modellek…/03` |
| **Megszakító** | circuit breaker | Sorozatos hiba után egy ideig nem hívjuk a szolgáltatót | `08-modellek…/03` |

## D. Tudás és tanulás

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **Hipotézis** | `hypothesis` | Ellenőrizetlen állítás vagy kód (pl. modell-kimenet); nem gyors-út válasz | `00-alapok/02` |
| **Ellenőrzött tudás** | `verified` | Teszttel, több forrással vagy a felhasználó által megerősítve | `05-tanulas/04` |
| **Elavult / cáfolt** | `stale` / `refuted` | Lejárt TTL vagy bukott újraellenőrzés / bizonyítottan hibás | `01-architektura/04` |
| **Vitatott / archivált** | `contested` / `archived` | A források vagy az ismétlés ellentmond, de a hiba nem bizonyított / régóta nem használt, nem törölt | `05-tanulas/03` |
| **Karantén** | = `hypothesis` | A `hypothesis` magyar neve a tanulási fájlokban; kódban mindig `hypothesis` | `05-tanulas/04` |
| **Bizalmi pontszám** | trust score (0..1) | Mennyire hihető egy elem vagy forrás | `03-web-szorfozes/03` |
| **Eredet** | provenance | Honnan jött egy elem (forrás, epizód, modell) — kötelező | `01-architektura/04` |
| **Beágyazás** | embedding | Szöveg → vektor (`embeddinggemma`), jelentés szerinti kereséshez | `01-architektura/04` |
| **Teljes szöveges keresés** | full-text search (FTS5) | SQLite szó szerinti keresés rangsorolással | `01-architektura/04` |
| **RAG** | retrieval-augmented generation | A modell a visszakeresett tudás alapján fogalmaz | `04-nyelv…/01` |
| **Szemantikus cache** | semantic cache | Jelentésben hasonló korábbi kérdés ellenőrzött válasza | `08-modellek…/04` |
| **Frissesség / TTL** | freshness / time-to-live | Meddig érvényes egy elem (témától függ) | `08-modellek…/04` |
| **Domain-bizalom** | domain trust | Egy webhely alap-megbízhatósága (`autolearn/trust.ts`) | `03-web-szorfozes/03` |
| **Lényegkivonás** | key-content extraction | Egy oldal/válasz lényegének kiemelése (`extractKeyContent`) | `03-web-szorfozes/02` |
| **Desztilláció** | distillation | Modellválasz → agy; nálunk csak hipotézisként | `00-alapok/02` |
| **Éjszakai önálló tanulás** | nightly self-study | Tétlenségben futó tanulási ciklusok | `05-tanulas/02` |
| **Tananyag** | curriculum | Rendezett témák és gyakorlófeladatok | `06-programozas/02` |
| **Ismétlés (térközös)** | spaced repetition | Ellenőrzött tudás időnkénti újraellenőrzése | `05-tanulas/03` |
| **Konszolidáció / felejtés** | consolidation / forgetting | Összevonás, tömörítés; a haszontalan elemek kivezetése | `05-tanulas/03` |

## E. Programozás, mérés

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **Tesztvezérelt gondolkodás** | test-driven thinking (TDD) | Előbb a tesztek (a „kész” definíciója), utána a kód | `06-programozas/05` |
| **Hiba-aláírás** | error signature | A hiba normalizált lenyomata (típus + hely); körforgás felismerésére | `06-programozas/06` |
| **Többfájlos projekt** | multi-file project | Több modul, közös tesztkészlet, lépésenkénti építés | `07-komplex-feladatok/03` |
| **Értékelő készlet** | evaluation set / benchmark | Rögzített feladatok, amiken a fejlődést mérjük; nem tanítjuk | `10-meres…/02` |
| **pass@1** | pass@1 | Első próbálkozásra (javítás nélkül) sikeres feladatok aránya | `06-programozas/09` |
| **Regresszió** | regression | Ami korábban ment, most bukik | `10-meres…/01` |
| **Kalibráció** | calibration | Mennyire egyezik a becsült és a tényleges sikerarány | `10-meres…/01` |
| **Fejlődési napló** | progress log | Időrendi mérési bejegyzések | `10-meres…/03` |
| **Fázis (P0–P6)** | phase | Az ütemterv lépései: P0 programozási ciklus … P6 felhő + kódolómodell + mérőfelület | `11-utemterv/01` |

## F. Biztonság és adatvédelem

| Fogalom | English / kódban | Jelentés itt | Hol |
|---|---|---|---|
| **Személyes adat** | personal data / PII | Név, születési adat, cím, elérhetőség, azonosító… — **soha** nem kerül az agyba | `09-biztonsag…/01` |
| **Titok** | secret | Jelszó, kulcs, token, kártyaszám — sehol nem tárolható | `09-biztonsag…/01` |
| **Kitakarás** | redaction | Személyes adat / titok cseréje helyőrzőre, mielőtt bármi kimegy | `08-modellek…/03` |
| **Prompt-injekció** | prompt injection | Külső tartalom, ami utasításnak álcázza magát | `09-biztonsag…/02` |
| **Vendég / bejelentkezett szint** | guest / user tier | Vendég: csak olvas, semmi személyes; bejelentkezve: saját fiók (RLS) | `01-architektura/03` |
| **RLS** | Row Level Security | Supabase-szabály: mindenki csak a saját sorait látja | `01-architektura/03` |
| **Tétlenség** | idle | A felhasználó nem használja a gépet / Aurit; ekkor futhat nehéz munka | `08-modellek…/02` |
| **Elővétel / megszakítás** | preemption | A háttérmunka félbeszakad, ha a felhasználó jön; ellenőrzőponttól folytatható | `01-architektura/02` |
| **Licenc** | license | Csak engedélyezett licencű tananyag és kód tárolható, forrással | `05-tanulas/05` |

## Kapcsolódó

- [../thinking.md](../thinking.md) — a fő dokumentum
- [01-mit-jelent-gondolkodni.md](01-mit-jelent-gondolkodni.md) · [02-oszinte-korlatok.md](02-oszinte-korlatok.md) · [03-tenyek-es-meresek.md](03-tenyek-es-meresek.md)
- [../01-architektura/01-attekintes.md](../01-architektura/01-attekintes.md) — a komponensek kapcsolata
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) — státuszok és eredet a sémában
