# Auri AI Server — Upgrade-prompt (v1 → v2): „jobb és gyorsabb”

> Ezt a promptot egy AI kódoló ügynöknek (pl. Claude Code) vagy fejlesztőnek add oda.
> Önálló, végrehajtható feladatleírás: kontextus + célok + prioritált feladatok +
> fájlszintű útmutató + mérhető elfogadási kritériumok. A meglévő `d:\Server` kódbázison dolgozz.

---

## 0. Szerepkör

Te egy senior Node.js/TypeScript backend- és teljesítmény-mérnök vagy. A feladatod egy
már működő, privát, ingyenes AI-inferencia-szerver **upgradelése**: tedd **gyorsabbá**
(elsősorban a válasz-latencia és a terhelés alatti áteresztőképesség), **megbízhatóbbá**
és **jobban üzemeltethetővé**, miközben a meglévő publikus API-felület és a CliMark-integráció
**visszafelé kompatibilis marad**. Ne írd újra az egészet — célzottan, fokozatosan, tesztekkel
alátámasztva fejlessz. Minden lépést indokolj, és minden állítást bizonyíts (parancs + kimenet).

---

## 1. A projekt jelenlegi állapota (tényszerű kiindulás)

A `d:\Server` egy TypeScript + Express 4 wrapper egy lokális **Ollama** köré, API-kulcsos védelemmel.
Windows 10 a célgép, Node 20+, CommonJS modulrendszer. A szerver szerepe: a CliMarkAI „Auri”
asszisztens provider-láncának egyik (ingyenes, korlátlan) eleme legyen, a Gemini → OpenAI → sablon
lánc elé/mögé bekötve.

**Fájlstruktúra és felelősségek (a valós kód alapján):**

- `src/index.ts` — Express bootstrap: `buildApp()` (CORS feltételesen, JSON limit `2mb`,
  `trust proxy`, 404, error-handler), `main()` graceful shutdown (SIGINT/SIGTERM, 5s hard-exit).
  A `buildApp()` exportált, hogy tesztelhető legyen; auto-start csak `require.main === module` esetén.
- `src/config.ts` — `dotenv/config` side-effect + kézi parserek (`parseList`, `parseInteger`,
  `parseBool`). A `config` objektum: `port`, `apiKeys` (vesszős, `auri_sk_CHANGE_ME` kiszűrve),
  `ollamaUrl` (trailing slash levágva), `ollamaModel`, `allowedOrigins`, `rateLimitPerMin`,
  `ollamaTimeoutMs`, `logPrompts`, `maxMessages`, `maxPromptChars`. `hasApiKeys()` guard.
- `src/auth.ts` — `requireApiKey` middleware: kulcs kinyerése `Authorization: Bearer` vagy
  `x-api-key` fejlécből, SHA-256 digest + `timingSafeEqual` (32 bájtos, konstans idejű), a kulcsok
  hash-ei cache-elve (`cachedHashes`). Sikernél `req.apiKeyMask` beállítva. Hibánál homályos `401`.
- `src/ollama.ts` — vékony Ollama-kliens natív `/api/chat` (NDJSON stream), `/api/tags` ellen.
  `chat()` (nem-stream), `chatStream()` (async generator, delta-chunkok majd `done` usage-dzsel),
  `listModels()`, `ping()` (sosem dob). `OllamaError` státusszal. `buildBody()` `options`-be teszi
  a `temperature`/`num_predict` értékeket. Usage: `prompt_eval_count` / `eval_count`.
- `src/routes/health.ts` — `GET /health` PUBLIKUS, mindig 200, `status: ok|degraded`, `model`,
  `ollama: up|down`, `uptime`.
- `src/routes/models.ts` — `GET /v1/models` VÉDETT, proxyzza az Ollama `/api/tags`-ját.
- `src/routes/chat.ts` — `POST /v1/chat` VÉDETT, a fő végpont. `validate()` (nem üres `messages`,
  `maxMessages`, role/content típus, `maxPromptChars`). Timeout + client-disconnect abort
  (`AbortController`, `res.on('close')`). Stream ágban SSE, a fejléceket az első chunkig halasztja
  (`ensureHeaders`), `data: {delta}`, majd `data: {usage, finish_reason}`, végül `data: [DONE]`.
  Nem-stream ág: JSON válasz. Hibatérkép: 400 (rossz body / model_not_found), 401, 429, 503.
- `src/util/logger.ts` — kézi structured logger (`info/warn/error`), `maskKey()` (prefix + utolsó 4).
- `src/util/rateLimit.ts` — in-memory **fixed-window** limiter, kulcs = `apiKeyMask || ip`,
  60s-os ablak, `setInterval` takarítás, `X-RateLimit-*` és `Retry-After` fejlécek, 429.
- `scripts/generate-key.ts` — `auri_sk_` + 36 random bájt base64url, `.env` upsert, keretes kiírás.
- `scripts/smoke.ts` — futó szerver ellen: /health, hiányzó/rossz kulcs → 401, üres messages → 400,
  és ha él az Ollama: valódi chat + stream. `process.exitCode` (nem `process.exit`, Windows libuv miatt).
- `package.json` — scriptek: `dev` (tsx watch), `build` (tsc), `start` (node dist), `typecheck`,
  `generate-key`, `smoke`. Függőségek: express, cors, dotenv; dev: tsx, typescript, @types/*.
- `tsconfig.json` — target ES2022, module CommonJS, `strict: true`, outDir `dist`.

**Ismert gyenge pontok / hiányok (ezeket célozzuk):**

1. **Hideg start / első válasz lassú** — az Ollama kirakja a modellt a memóriából tétlenség után;
   nincs `keep_alive`, nincs warmup boot-kor. (A README hibaelhárítása is említi.)
2. **Nincs konkurencia-kontroll** — CPU-n futó modellnél több párhuzamos kérés egymást fojtja;
   nincs sor/szemafor, így terhelés alatt minden lassú lesz, és timeoutok jönnek.
3. **Nincs HTTP keep-alive finomhangolás** az Ollama felé (undici default pool), nincs cache.
4. **Nincs OpenAI-kompatibilis végpont** (`/v1/chat/completions`) — pedig azzal rengeteg kliens/SDK
   azonnal rácsatlakozna, és a CliMark-integráció is egyszerűbb lenne.
5. **Nincs igazi teszt** (csak smoke), **nincs lint**, **nincs CI**, **nincs Docker**.
6. **Megfigyelhetőség korlátozott** — nincs request-id/korreláció, nincs `/metrics`, nincs log-szint.
7. **Rate limit fixed-window** — ablakhatáron burst-ölhető; nincs globális konkurencia-limit,
   nincs per-kulcs külön limit.
8. **Graceful shutdown nem várja meg a futó streameket** (csak `server.close` + 5s hard-exit).
9. **Config-validáció minimális** — hibás env esetén néma fallback, nincs jól olvasható hibaüzenet.

---

## 2. A küldetés: mérhető célok

Az upgrade akkor sikeres, ha az alábbiak **számszerűen** teljesülnek (lásd Elfogadási kritériumok):

- **Latencia:** a *második és további* nem-stream válasz first-byte-ig tartó ideje érdemben csökken
  a warmup + `keep_alive` miatt; a hideg start eltűnik a normál üzemből.
- **Stream first-token:** az első `data: {delta}` esemény a lehető leghamarabb menjen ki
  (ne pufferelődjön); legyen heartbeat, hogy a proxy ne zárja a kapcsolatot.
- **Terhelés alatti stabilitás:** N párhuzamos kérésnél ne thrash-eljen a gép — kontrollált sorral
  a p95 latencia és a hibaarány drámaian javuljon a jelenlegihez képest.
- **Visszafelé kompatibilitás:** a meglévő `POST /v1/chat`, `GET /v1/models`, `GET /health`
  kérés/válasz alakja **nem törhet**; a CliMark `callAuriServer()` snippet változtatás nélkül működjön.
- **Minőség/üzemeltetés:** legyen automata tesztkészlet, lint, CI, Docker, és jobb observability.

Nem cél: fizetős API/GPU-felhő bevezetése, a „teljesen ingyenes, lokális” elv feladása,
multi-tenant felhasználókezelés, adatbázis bevezetése (hacsak egy feladat kifejezetten nem kéri).

---

## 3. Vezérelvek és megkötések (KÖTELEZŐ betartani)

1. **Visszafelé kompatibilitás mindenek előtt.** A meglévő végpontok szerződése nem változhat.
   Új viselkedés csak additív (új végpont, új opcionális mező, új env-kapcsoló, alapból a régi viselkedés).
2. **Ingyenes és lokális marad.** Csak nyílt/ingyenes eszközök. Az Ollama portja (`11434`) soha nem
   publikus; kifelé csak a védett szerver-port (`8787`). Ezt teszt/dok szinten is tartsd fenn.
3. **Windows-first, de hordozható.** A célgép Windows 10 + PowerShell. Minden script és parancs
   működjön Windowson; a Docker/Linux út legyen opcionális kiegészítés, ne kötelező függőség.
4. **Kis, felülvizsgálható lépések.** Logikai egységenként dolgozz; minden egység után fusson le a
   `typecheck`, `build`, `lint`, `test`. Ne keverj össze egy commitba sok, egymástól független dolgot.
5. **Biztonság ne romoljon.** A kulcs továbbra is maszkolva a logokban, soha nincs prompt-tartalom
   logban `LOG_PROMPTS=false` mellett, a 401 marad homályos. Új biztonsági réteg csak additív.
6. **Konfig minden új viselkedéshez env-kapcsolóval**, értelmes alapértékkel; a meglévő `.env`
   változatlanul tovább működjön. Frissítsd a `.env.example`-t és a README-t minden új kapcsolóra.
7. **Mérj, ne tippelj.** Sebesség-állításhoz adj reprodukálható mérést (parancs + nyers számok).
8. **Ne vezess be nehéz függőséget**, ha könnyű/standard megoldás is van (előnyben: Node beépített
   API-k, undici, kis fókuszált csomagok). Minden új dependencyt indokolj.

---

## 4. Feladatok prioritás szerint

> Dolgozz felülről lefelé. A P0 a „gyorsabb” mag; a P1 a megbízhatóság/observability; a P2 a
> minőség/üzemeltetés; a P3 nice-to-have. Egy feladatot se tekints késznek teszt + bizonyíték nélkül.

### P0 — Sebesség (a fő cél)

**P0.1 — Modell-warmup boot-kor és `keep_alive`.**
- Bővítsd a `src/ollama.ts` `buildBody()`-t egy `keep_alive` opcióval (Ollama natív mező; pl.
  `"30m"` vagy `-1` = soha ne kerüljön ki). Vezesd be a `OLLAMA_KEEP_ALIVE` env-et (`config.ts`),
  default `"30m"`. Add hozzá a non-stream és stream kérésekhez is.
- Indításkor (`index.ts` `main()`, miután a listen elindult) küldj egy **warmup** kérést az alap
  modellre (pl. egy rövid „ping” chat `num_predict: 1`-gyel, vagy az Ollama natív
  `POST /api/generate` üres prompttal, ami betölti a modellt). Ez **ne blokkolja** a boot-ot és
  **ne dőljön el** a szerver, ha az Ollama még nem fut (logold `warn`-ként, próbáld újra háttérben).
  Tedd kapcsolhatóvá: `WARMUP_ON_BOOT` (default `true`).
- Add hozzá egy belső `warmup()` függvényt az `ollama.ts`-be, amit a `/health` is meghívhat opcionálisan.

**P0.2 — Konkurencia-kontroll (sor + szemafor) az inferenciára.**
- Vezess be egy kicsi, függőség nélküli **szemafort/sort** (`src/util/concurrency.ts`): max N
  egyidejű Ollama-hívás (`OLLAMA_MAX_CONCURRENCY`, default 1 CPU-modellnél, mert egy 3B CPU-n
  gyakorlatilag szekvenciális). A többi kérés várjon sorba egy korlátos várólistában
  (`OLLAMA_QUEUE_LIMIT`, default pl. 20); a limiten túli kérés azonnal `503 server_busy`
  (`Retry-After`-rel), ne torlódjon a végtelenségig.
- Kösd be a `chat.ts` mindkét ágába (stream és non-stream) úgy, hogy a szemafor **a kliens-abortot**
  és a **timeoutot** is tisztán kezelje (sorban állás közbeni lemondásnál ne foglaljon helyet).
- Adj a `/health`-hez (vagy `/metrics`-hez) `inflight` és `queued` számlálót.

**P0.3 — HTTP keep-alive és kapcsolat-újrahasználás az Ollama felé.**
- Hozz létre egy dedikált undici `Agent`-et (keep-alive, ésszerű pool méret, `headersTimeout`/
  `bodyTimeout` a stream miatt nagyra/0-ra állítva) és add át a `fetch` hívásoknak (`dispatcher`).
  Cél: ne épüljön fel új TCP minden hívásnál. Tedd a `ollama.ts`-be, egy helyen.

**P0.4 — Opcionális válasz-cache (determinisztikus kérésekre).**
- Vezess be egy kicsi **LRU cache**-t (`src/util/cache.ts`, függőség nélkül vagy egy apró LRU
  csomaggal) a **nem-stream** `/v1/chat` válaszokra, kulcs = hash(model + messages + temperature +
  max_tokens). **Csak** `temperature <= 0` (vagy `CACHE_ONLY_DETERMINISTIC=true`) esetén cache-elj,
  TTL-lel (`RESPONSE_CACHE_TTL_MS`) és méretkorláttal (`RESPONSE_CACHE_MAX`). Alapból
  `RESPONSE_CACHE=false` (additív, opt-in). Cache-találatnál `X-Cache: HIT` fejléc, a usage maradjon
  konzisztens. Streamet ne cache-elj az első körben.

**P0.5 — Ollama futtatási opciók kihangolása.**
- Engedd át kérésenként és/vagy env-ből a fontos Ollama `options`-öket: `num_ctx`, `num_thread`,
  `num_batch`, `num_gpu`/`num_gpu_layers`, `top_p`, `stop`, `seed`. A body-ban opcionálisan,
  env-ben defaultként (`OLLAMA_NUM_CTX`, `OLLAMA_NUM_THREAD`, …). Validáld a típusokat. Dokumentáld,
  hogy ezek hogyan befolyásolják a sebességet/minőséget (kisebb `num_ctx` = gyorsabb).

### P0 — OpenAI-kompatibilis végpont (nagy érték, additív)

**P0.6 — `POST /v1/chat/completions` (OpenAI-kompatibilis).**
- Új route (`src/routes/chatCompletions.ts`), ugyanazon auth + rate limit + szemafor mögött.
- Fogadd az OpenAI chat completions body-t (`model`, `messages`, `temperature`, `max_tokens`,
  `stream`, `stop`, `top_p`, `seed`). Mappeld az Ollama-hívásra (a meglévő `chat`/`chatStream`-et
  használd újra). A **válasz** alakja egyezzen az OpenAI-éval:
  - non-stream: `{ id, object:"chat.completion", created, model, choices:[{index,message:{role,content},finish_reason}], usage:{prompt_tokens,completion_tokens,total_tokens} }`
  - stream: SSE `data: {chat.completion.chunk …}` darabok, lezárás `data: [DONE]`.
- Így bármely OpenAI-kompatibilis kliens (és a CliMark OpenAI-ága is) átirányítható a saját szerverre
  `baseURL` cserével. A meglévő `/v1/chat` **maradjon** változatlanul (ne töröld).

### P1 — Megbízhatóság

**P1.1 — Retry tranziens hibákra.** Az `ollama.ts` `postChat`/`listModels` kapjon korlátozott,
exponenciális backoffos újrapróbálkozást **csak** tranziens esetekre (connection refused/reset, 502,
503; `ECONNRESET`), max 2 próbával, jitterrel. 4xx (pl. 404 model_not_found) **soha** ne legyen
retry-olva. A streamet csak akkor próbáld újra, ha még nem ment ki egyetlen chunk sem.

**P1.2 — Request-id / korreláció.** Generálj minden kéréshez egy `requestId`-t (vagy fogadd az
`X-Request-Id` fejlécet), tedd a logokba és a hibaválaszok body-jába (`error`, `request_id`).
Add vissza `X-Request-Id` válaszfejlécként.

**P1.3 — Igazi graceful drain.** A shutdown ne csak `server.close`-oljon: tartson számon az
**in-flight** kérésekről, hagyjon nekik egy konfigurálható türelmi időt (`SHUTDOWN_GRACE_MS`,
default ~10s) a befejezésre, közben utasítsa el az újakat `503`-mal (`Connection: close`).
A futó streameket szépen zárja le (`data: [DONE]` vagy `stream_error` esemény).

**P1.4 — Egységes hibamodell.** Vezess be egy `AppError`/`HttpError` típust (kód + status + üzenet)
és egy közös JSON-hibaformázót, hogy minden végpont konzisztens `{ error, message?, request_id }`-t
adjon. Az Ollama-hibák státusz-térképe maradjon (404→400 model_not_found, egyéb→502/503).

### P1 — Megfigyelhetőség

**P1.5 — Strukturált, szintezett logging.** Cseréld/bővítsd a `logger.ts`-t: legyen `LOG_LEVEL`
(`debug|info|warn|error`) és `LOG_FORMAT` (`text|json`). Maradjon a kulcs-maszkolás és a
prompt-védelem. (Választható: `pino` bevezetése, ha indokolt — de tartsd a maszkolást és a jelenlegi
mezőket.) Minden chat-log tartalmazza: `requestId`, `model`, `stream`, `tokens`, `durationMs`,
`queuedMs`, `key` (maszkolt), és stream esetén a **first-token latenciát** (`ttftMs`).

**P1.6 — `/metrics` végpont.** Adj egy **publikus vagy védett** (kapcsolható) `/metrics`-et
Prometheus-formátumban vagy egy egyszerű JSON-nal: kérésszám végpontonként/státuszonként,
latencia-hisztogram (vagy p50/p95), `inflight`, `queued`, cache hit/miss, Ollama up/down,
process uptime/mem. Ne szivárogtass kulcsot/prompt-tartalmat.

**P1.7 — `/health` bővítés.** A meglévő mezők maradjanak; adj hozzá (additív) `version`,
`inflight`, `queued`, és opcionálisan a betöltött modell állapotát. Maradjon mindig 200 + `degraded`.

### P1 — Biztonság

**P1.8 — `helmet` és szigorítások.** Tedd be a `helmet`-et (értelmes defaultokkal), tartsd meg az
`x-powered-by` letiltást. A `2mb` JSON-limit legyen env-ezhető (`MAX_BODY_SIZE`). Adj opcionális
**IP-allowlistet** (`IP_ALLOWLIST`, üres = mindenki), ami a `trust proxy` miatt a valódi kliens-IP-t
nézi (Cloudflare). Adj opcionális egyszerű **/health rate-limitet** is a publikus végpontra (DoS ellen).

**P1.9 — Jobb rate limiting.** Cseréld a fixed-windowt **token-bucket** vagy **sliding-window**
algoritmusra (ablakhatár-burst megszüntetése). Tedd lehetővé a **per-kulcs** limit-felülírást
(pl. `RATE_LIMITS=auri_sk_aaa:120,auri_sk_bbb:30`) és a globális defaultot. Tartsd meg az
`X-RateLimit-*` és `Retry-After` fejléceket. Maradjon in-memory, de a modul legyen úgy megírva,
hogy később Redis-backend becsatolható legyen (interfész mögé).

### P2 — Tesztelés és minőség

**P2.1 — Unit + integrációs tesztek (Vitest).**
- Vezesd be a **Vitest**-et. Írj unit teszteket: `auth` (jó/rossz/hiányzó kulcs, több kulcs,
  konstans idejű ág), `config` parserek, `rateLimit` (token bucket határesetek), `validate`
  (chat body élhelyzetek), `concurrency` (sor/limit/abort), `cache` (TTL/LRU/determinizmus),
  `ollama` usage-mappelés és hibatérkép.
- Integrációs tesztek: indíts egy **mock Ollama** szervert (kis Express/http, ami NDJSON streamet és
  `/api/tags`-et ad), és teszteld a `buildApp()`-ot supertest-szerűen (vagy `fetch`-csel egy
  ефemer porton): `/health`, `/v1/models`, `/v1/chat` (stream és non-stream, hibák, abort, timeout),
  `/v1/chat/completions` (OpenAI alak), rate limit 429, server_busy 503.
- Cél: **érdemi lefedettség** a route-okra és a kritikus utilokra. Adj `npm test` és
  `npm run test:watch` scriptet. A CI-ban fusson le.

**P2.2 — ESLint + Prettier.** Tedd be az ESLint-et (`@typescript-eslint`) és a Prettier-t, közös
configgal. Add `npm run lint` és `npm run format` scripteket. A meglévő
`// eslint-disable-next-line @typescript-eslint/no-namespace` komment így valós configot kap.
Javítsd a lint-hibákat. (Választható: `husky` + `lint-staged` pre-commit hook.)

**P2.3 — `smoke.ts` bővítése.** A meglévő 5 ellenőrzés maradjon; tegyél hozzá: `/v1/chat/completions`
alak-ellenőrzés, `X-Request-Id` jelenléte, rate-limit 429 kiváltása, server_busy ág (ha kikényszeríthető),
és stream first-token mérés. Maradjon `process.exitCode`-os kilépés (Windows libuv).

### P2 — Üzemeltetés / deploy

**P2.4 — Docker + docker-compose.** Adj egy többlépcsős `Dockerfile`-t (build → karcsú runtime,
non-root user, `HEALTHCHECK` a `/health`-re) és egy `docker-compose.yml`-t, ami **Ollama + a szerver
együtt** indítja (Ollama service belső hálón, csak a szerver portja kitéve). Dokumentáld, hogy
GPU-s gépen hogyan kell az Ollama image-et GPU-ra kötni (opcionális). A Windows-os lokális út
(npm) maradjon az elsődleges; a Docker legyen alternatíva (pl. Oracle Free VPS-hez).

**P2.5 — „Mindig fusson” receptek.** Adj kész leírást/configot legalább kettőre: (a) **PM2** vagy
**Windows Service** (pl. `node-windows`/NSSM) a szerver autostarthoz Windowson; (b) **systemd** unit
Linux/VPS-re; (c) **cloudflared** named tunnel `config.yml` sablon, ami a `8787`-re mutat (sose a
`11434`-re). Ezek a README-be és/vagy egy `deploy/` mappába kerüljenek.

**P2.6 — `.env.example` + README szinkron.** Minden új env-kapcsolót vezess át a `.env.example`-be
értelmes alapértékkel és magyar kommenttel, és frissítsd a README megfelelő tábláit/szakaszait
(Konfiguráció, Végpont-referencia az új `/v1/chat/completions`-szel és `/metrics`-szel, Teljesítmény
szakasz a warmup/keep_alive/konkurencia magyarázatával, Hibaelhárítás a `503 server_busy`-vel).

### P2 — Funkcionális bővítés

**P2.7 — `POST /v1/embeddings`.** Implementáld (a README már „jövőbeli”-ként említi): proxyzd az
Ollama `/api/embeddings`-ét (`nomic-embed-text` modellel), auth + rate limit mögött, OpenAI-szerű
válaszalakkal (`{ object:"list", data:[{embedding,index}], model, usage }`). Külön env a default
embedding-modellre (`OLLAMA_EMBED_MODEL`). Maradjon opcionális; ha a modell nincs letöltve, tiszta 400.

### P3 — Nice-to-have

- **OpenAPI/Swagger** leírás a végpontokról (`openapi.yaml` + opcionális `/docs`).
- **Model-alias térkép** (`MODEL_ALIASES=fast:gemma2:2b,smart:qwen2.5:3b-instruct`), hogy a CliMark
  logikai neveket küldhessen.
- **Stream heartbeat** finomítás: SSE komment-ping (`: ping\n\n`) konfigurálható időközzel, hogy a
  proxy ne bontson tétlen streamnél.
- **Naplórotáció** fájlba (opcionális), ha nem stdout-only az üzemeltetés.

---

## 5. Fájlszintű útmutató (hol mit érints)

- `src/config.ts` — itt vezesd be az ÖSSZES új env-kapcsolót, ugyanazzal a parser-stílussal
  (`parseInteger`/`parseBool`/`parseList`). Adj egy `validateConfig()`-ot, ami induláskor érthető
  hibát dob a rosszul megadott értékekre (pl. negatív timeout), és figyelmeztet a gyanús
  beállításokra. Tartsd a `as const` jelleget vagy típusold explicit interfésszel.
- `src/ollama.ts` — ide jön a keep-alive undici `Agent`, a `keep_alive` opció, a `warmup()`, a retry,
  és az extra `options` átvezetése. A publikus függvény-szignatúrák maradjanak kompatibilisek.
- `src/util/concurrency.ts` (új) — szemafor + korlátos sor, abort-aware. Tiszta, tesztelhető API.
- `src/util/cache.ts` (új) — LRU + TTL, tiszta API, tesztelhető.
- `src/util/metrics.ts` (új) — számlálók/hisztogramok gyűjtése, `/metrics` rendereléshez.
- `src/middleware/` (új mappa lehet) — `requestId`, `errorHandler`, `ipAllowlist`, `helmet` bekötés.
- `src/routes/chat.ts` — kösd be a szemafort, request-id-t, ttft-mérést, ne törd a meglévő alakot.
- `src/routes/chatCompletions.ts` (új), `src/routes/metrics.ts` (új), `src/routes/embeddings.ts` (új).
- `src/index.ts` — helmet, requestId middleware, új route-ok regisztrálása, warmup hívás,
  igazi graceful drain. A `buildApp()` maradjon exportált és tesztelhető.
- `scripts/smoke.ts` — bővítés (P2.3). `scripts/bench.ts` (új) — egyszerű terhelés/latencia mérő
  (lásd lent), hogy a sebesség-állításokat bizonyítani lehessen.
- `tests/` (új) — Vitest unit + integráció, mock Ollama helper.
- `Dockerfile`, `docker-compose.yml`, `deploy/` (új), `.dockerignore`, `eslintrc`, `.prettierrc`,
  `.github/workflows/ci.yml` (új).

---

## 6. Teszt- és bizonyítási terv (KÖTELEZŐ a leadáshoz)

1. **Statikus:** `npm run typecheck` → 0 hiba; `npm run lint` → 0 hiba; `npm run build` → siker.
2. **Egység/integráció:** `npm test` → minden zöld; mutasd a futás kimenetét és a lefedettséget.
3. **Smoke:** `npm run smoke` futó szerver ellen → minden eddigi + új ellenőrzés passed.
4. **Sebesség-bench (`scripts/bench.ts`):** írj egy kis mérőt, ami M kérést K párhuzamossággal küld
   a `/v1/chat`-re (rögzített rövid prompt, `max_tokens` kicsi), és kiírja: total, RPS, p50/p95/p99
   latencia, hibaarány, átlag ttft (stream esetén). Futtasd **a változtatások előtt és után**
   (ha Ollama elérhető), és mutasd a két számsort egymás mellett. Ha az Ollama nem telepíthető a
   gépen, akkor a mock-Ollama ellen mérj (a sor/keep-alive/agent hatása így is látszik a wrapper
   rétegen), és ezt jelezd. **Ne állíts gyorsulást mérés nélkül.**
5. **Kompatibilitás-bizonyíték:** mutasd, hogy a régi `POST /v1/chat` és a CliMark `callAuriServer()`
   snippet változatlanul működik (pl. a snippetet futtató kis teszt vagy curl-példa kimenete).
6. **Biztonság:** mutasd, hogy a 401 továbbra is homályos, a kulcs maszkolt a logokban, és
   `LOG_PROMPTS=false` mellett nincs prompt-tartalom a logban.

A leadáskor minden állításhoz tartozzon a parancs + a nyers kimenet. Ha valamit nem tudtál élesben
igazolni (pl. Ollama nincs telepítve a CI-ben), azt **írd le egyértelműen**, és add meg a pontos
parancsot, amivel a felhasználó lokálisan igazolhatja.

---

## 7. Amit NE csinálj

- Ne törd a meglévő végpontok kérés/válasz-alakját, ne nevezz át publikus mezőt.
- Ne tedd kötelezővé a Dockert/Redist/adatbázist; ezek opcionális utak.
- Ne tedd publikussá az Ollama portját, és ne logolj kulcsot vagy prompt-tartalmat alapból.
- Ne vezess be nehéz keretrendszert (pl. NestJS) — maradjon vékony Express.
- Ne `process.exit`-elj ott, ahol a természetes loop-drain a helyes (Windows libuv assertion).
- Ne állíts teljesítményjavulást konkrét mérés nélkül.
- Ne hagyj „majdnem kész” kódot teszt és bizonyíték nélkül.

---

## 8. Leadás formátuma

A munka végén adj:

1. **Rövid összefoglalót** arról, mit változtattál, fájlonként/feladatonként (P0…P3 szerint).
2. **Mérési eredményeket** (előtte/utána, ha lehetséges) a sebesség-feladatokhoz.
3. **A futtatási bizonyítékokat** (typecheck/lint/build/test/smoke/bench kimenetek).
4. **Frissített README + `.env.example`** összefoglalót (mi az új env, mi az új végpont).
5. **Migrációs megjegyzést** a CliMark felé: hogyan állhat át opcionálisan a
   `/v1/chat/completions`-re (baseURL csere), és hogy a régi út is megmarad.
6. **Maradék kézi lépéseket** (pl. „telepítsd az Ollamát + `ollama pull …` az éles inferenciához”),
   pontos parancsokkal.

---

## 9. Javasolt sorrend (egy lehetséges végrehajtási terv)

1. Alap higiénia: ESLint+Prettier+Vitest beállítása, `validateConfig()`, request-id + errorHandler
   middleware, structured/leveled logger. (Stabil alap a többihez, gyorsan tesztelhető.)
2. Sebesség-mag: undici keep-alive Agent → `keep_alive` + warmup → konkurencia-sor/szemafor →
   `bench.ts` + előtte/utána mérés.
3. OpenAI-kompatibilis `/v1/chat/completions` (újrahasználva a meglévő klienst) + tesztek.
4. Megbízhatóság: retry, igazi graceful drain, egységes hibamodell.
5. Observability: `/metrics`, `/health` bővítés, ttft-log.
6. Biztonság: helmet, IP-allowlist, token-bucket rate limit (+ per-kulcs).
7. Opcionális válasz-cache, extra Ollama-opciók.
8. Deploy: Docker(+compose), PM2/systemd/Windows service, cloudflared sablon, CI workflow.
9. Embeddings végpont, majd a P3 nice-to-have-ek igény szerint.
10. README + `.env.example` teljes szinkron, végső teszt/bench/smoke futás és leadás.

> Minden lépés után: `typecheck` + `lint` + `build` + `test` zölden, és csak akkor lépj tovább.
> Kérdezz vissza, ha egy döntés érdemben befolyásolja a CliMark-kompatibilitást.

---

## 10. Teljesítmény-háttér: miért és mennyit gyorsítanak az egyes lépések

Ez a szakasz azért fontos, hogy ne vakon, hanem a mechanizmusok megértésével optimalizálj. A lokális,
CPU-n futó kis modelleknél (3B körül) a latencia három fő összetevőből áll: (1) **modellbetöltés**
(load) a memóriába, (2) **prompt feldolgozás** (prefill, a `prompt_eval`), és (3) **token-generálás**
(decode, az `eval`). A wrapper rétegnek mindháromra van ráhatása, vagy közvetlenül, vagy a hívási
mintázaton keresztül.

- **Modellbetöltés (a legnagyobb single-shot költség).** Az Ollama tétlenség után kirakja a modellt a
  memóriából, és a következő kérés újra betölti — ez másodperceket, lassabb gépen tíz másodperc
  nagyságrendet is jelenthet. A `keep_alive` (P0.1) ezt megszünteti azzal, hogy a modellt bent tartja;
  a boot-warmup pedig a *legelső* éles kérés latenciáját tolja át az indulási fázisba, ahol senki nem
  várja. Együtt: a normál üzemből gyakorlatilag eltűnik a hideg start. Ezt a `bench.ts` első vs.
  sokadik kérés latenciájának összevetésével lehet bizonyítani.

- **Prompt-prefill újrahasználása.** Az Ollama a betöltött modellnél képes a korábbi prompt-kontextus
  egy részét újrahasználni (prompt cache), ezért a stabil, ismétlődő **system prompt** olcsóbbá válik,
  ha a modell bent marad. A `keep_alive` ezt is segíti. A kisebb `num_ctx` (P0.5) csökkenti a prefill
  költségét — ha a használati eset nem igényel hosszú kontextust, ez érezhető gyorsulás minőségvesztés
  nélkül. Ezt env-defaulttal és kérésenkénti felülírással is engedd.

- **Konkurencia és sorbanállás.** Egyetlen CPU-modell egyszerre érdemben egy generálást tud hatékonyan
  futtatni; ha öt kérés egyszerre érkezik, és mind „beenged”, a gép cache-e és szálai egymást fojtják,
  és **mindegyik** lassú lesz, sőt timeoutolhat. A szemafor (P0.2) szerializálja a tényleges
  inferenciát, a korlátos sor pedig megvédi a szervert a végtelen torlódástól (gyors `503 server_busy`
  a reménytelen kérésekre, ahelyett hogy 60s-ot várnának egy timeoutra). Ez nem növeli az egyedi kérés
  sebességét, de drámaian javítja a terhelés alatti **p95/p99 latenciát és a hibaarányt** — ezt a
  `bench.ts` magas párhuzamossággal (pl. K=8) futtatva mutasd ki.

- **Kapcsolat-újrahasználat.** Az undici keep-alive `Agent` (P0.3) megspórolja a TCP/HTTP kézfogást az
  Ollama felé minden hívásnál. Önmagában kicsi, de sok rövid kérésnél és streamnél összeadódik, és
  csökkenti a jittert. A streamnél figyelj a `bodyTimeout`/`headersTimeout` helyes (nagy vagy 0)
  beállítására, különben hosszú generálásnál a kliens idő előtt elvágódik.

- **Válasz-cache.** A determinisztikus (`temperature<=0`) ismétlődő kérések cache-elése (P0.4) a
  generálást teljesen kihagyja — ez a leggyorsabb „válasz”, ami létezik (memóriából, ~0 ms). Csak ott
  alkalmazd, ahol a determinizmus garantált, és jelezd `X-Cache: HIT`-tel, hogy mérhető és átlátható
  legyen. A streamet az első körben szándékosan ne cache-eld, mert a darabolt kimenet újrajátszása
  bonyolultabb, és kisebb a nyereség.

- **First-token latencia (ttft) streamnél.** A felhasználó által *érzékelt* sebességet stream esetén
  nem a teljes idő, hanem az **első token megjelenése** dominálja. Ezért a `chat.ts` SSE-ágában az
  első `delta`-t a lehető leghamarabb küldd ki (a fejléceket halaszd, de a flush legyen azonnali),
  kapcsold ki a proxy-pufferelést (`X-Accel-Buffering: no`, már megvan), és mérd a `ttftMs`-t a
  logban. A heartbeat-ping (P3) megakadályozza, hogy egy lassú prefill alatt a proxy lezárja a streamet.

Az alapelv: a **„gyorsabb”** célt elsősorban a hideg start megszüntetése (keep_alive + warmup), a
terhelés alatti viselkedés rendbe tétele (szemafor + sor) és az érzékelt latencia javítása (ttft +
heartbeat) adja; a cache és a kapcsolat-újrahasználat ráadás. Mindig a `bench.ts` előtte/utána
számaival bizonyíts, ne az intuícióval.

---

## 11. Függelék: env-változó referencia (régi + új)

A meglévő kapcsolók maradnak (`PORT`, `AURI_API_KEY`, `OLLAMA_URL`, `OLLAMA_MODEL`,
`ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MIN`, `OLLAMA_TIMEOUT_MS`, `LOG_PROMPTS`, `MAX_MESSAGES`,
`MAX_PROMPT_CHARS`) — ezek viselkedése **nem változhat** alapértéken. Az alább javasolt új kapcsolók
mind opcionálisak, és a defaultjuk a jelenlegi viselkedést őrzi meg (vagy biztonságos kiterjesztés):

- `OLLAMA_KEEP_ALIVE` (default `30m`) — meddig tartsa bent az Ollama a modellt.
- `WARMUP_ON_BOOT` (default `true`) — boot-warmup be/ki.
- `OLLAMA_MAX_CONCURRENCY` (default `1`) — egyidejű inferenciák maximuma.
- `OLLAMA_QUEUE_LIMIT` (default `20`) — várólista maximális hossza, felette `503 server_busy`.
- `RESPONSE_CACHE` (default `false`), `RESPONSE_CACHE_TTL_MS`, `RESPONSE_CACHE_MAX`,
  `CACHE_ONLY_DETERMINISTIC` (default `true`).
- `OLLAMA_NUM_CTX`, `OLLAMA_NUM_THREAD`, `OLLAMA_NUM_BATCH`, `OLLAMA_NUM_GPU` — Ollama runtime opciók.
- `LOG_LEVEL` (default `info`), `LOG_FORMAT` (default `text`).
- `MAX_BODY_SIZE` (default `2mb`), `IP_ALLOWLIST` (default üres = mindenki).
- `RATE_LIMITS` (per-kulcs felülírás, pl. `auri_sk_aaa:120,auri_sk_bbb:30`).
- `SHUTDOWN_GRACE_MS` (default `10000`) — graceful drain türelmi idő.
- `OLLAMA_EMBED_MODEL` (default pl. `nomic-embed-text`) — embeddings végponthoz.
- `METRICS_PROTECTED` (default `true`) — a `/metrics` kulcs mögött legyen-e.
- `MODEL_ALIASES` (opcionális) — logikai modellnév → valós Ollama-modell térkép.

Minden itt felsoroltat vezess át a `.env.example`-be (magyar kommenttel, biztonságos defaulttal) és a
README Konfiguráció-táblájába, hogy a dokumentáció és a kód egyetlen igazságforrásból szinkronban legyen.
