# Kódtudástár — ellenőrzött snippetek és API-index

> **Miről szól:** a „bevált kód” könyvtára: minden snippet **kóddal + tesztjeivel + verziókkal + forrással +
> licenccel + bizalmi szinttel + használati statisztikával** együtt él. Visszakeresés FTS5 + beágyazás
> kombinációjával. Leírja, hogyan nő ki a meglévő `programmingCurated.ts` / `recipes.ts` / `sources.ts` seedből.

## 1. Mi kerül be — és mi nem

| Be | Nem |
|---|---|
| a TDD-ciklus zöld megoldásai ([05](05-tesztvezerelt-gondolkodas.md)), tesztjeikkel | futtatás nélküli modellválasz „tényként” (az legfeljebb T0) |
| kurált seed (eredeti idiómák), dokumentáció kódpéldái engedett licenccel | ismeretlen licencű szöveg vagy kód (csak link) |
| saját repóból kinyert minták **szűrés után** ([07](07-sajat-projektekbol-tanulas.md)) | titok, `.env`-tartalom, személyes adat (`isPersonal`, `web/src/brain/privacy.ts`) |
| hibajavítási receptek ([06](06-hibakereses.md)) | a `dev`/`heldout` mérőkészlet feladatainak megoldásai ([09](09-meres-es-benchmark.md)) |

Méretkorlát: egy snippet ≤ 80 sor. Ami nagyobb, az **projektsablon** (`ProjectTemplate`, 7. pont).

## 2. Séma

```ts
type Trust = 0 | 1 | 2 | 3 | 4;                       // T0..T4 (3. pont)
interface VerifiedSnippet {
  id: string;                                          // 'snip_ts_slugify_hu_01'
  lang: 'ts' | 'js' | 'py' | 'sql' | 'css' | 'html';
  title: string;  summary_hu: string;                  // mit csinál, mikor használd (1–2 mondat)
  code: string;                                        // szó szerint
  tests: { framework: 'node:test' | 'pytest' | 'sqlite' | 'static'; code: string }[];
  env: { node?: string; python?: string; typescript?: string; deps?: Record<string, string> };
  topics: string[];                                    // tananyag-témák (02)
  symbols: string[];                                   // használt API-k: 'Array.prototype.map', 'pathlib.Path'
  source: { kind: 'own-loop' | 'curated' | 'doc' | 'web' | 'own-repo';
            url?: string; repoPath?: string; commit?: string;
            license: string; attribution?: string };   // SPDX-azonosító, 'own' vagy 'unknown'
  trust: Trust;
  verification: { status: 'pass' | 'fail' | 'never'; runId?: string; at?: string; sandbox?: 'S0' | 'S1' };
  usage: { retrieved: number; usedInSolution: number; solutionPassed: number; lastUsedAt?: string };
  createdAt: string; updatedAt: string; supersededBy?: string;
}
```

Tárolás (P1-től az Auri Core SQLite-jában, [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md)):

```sql
CREATE TABLE snippet (
  id TEXT PRIMARY KEY, lang TEXT NOT NULL, title TEXT NOT NULL, summary_hu TEXT, code TEXT NOT NULL,
  code_hash TEXT NOT NULL, env_json TEXT NOT NULL, topics_json TEXT, symbols_json TEXT,
  source_kind TEXT NOT NULL, source_url TEXT, license TEXT NOT NULL,
  trust INTEGER NOT NULL DEFAULT 0, verify_status TEXT NOT NULL DEFAULT 'never', last_run_id TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, superseded_by TEXT REFERENCES snippet(id)
);
CREATE TABLE snippet_test (snippet_id TEXT REFERENCES snippet(id), framework TEXT NOT NULL, code TEXT NOT NULL);
CREATE TABLE snippet_use  (snippet_id TEXT, task_id TEXT, outcome TEXT CHECK (outcome IN ('pass','fail')), at TEXT);
CREATE TABLE snippet_vec  (snippet_id TEXT PRIMARY KEY, model TEXT NOT NULL, dim INTEGER NOT NULL, vec BLOB NOT NULL);
CREATE VIRTUAL TABLE snippet_fts USING fts5(
  snippet_id UNINDEXED, title, summary_hu, code, symbols,
  tokenize = 'unicode61 remove_diacritics 2'          -- ékezetfüggetlen keresés ("fuggveny" = "függvény")
);
```

Az FTS nem bontja szét a `camelCase`/`snake_case` azonosítókat, ezért beszúráskor a `symbols` oszlopba a
szétbontott alakot is írjuk (`readFile` → `readFile read file`).

## 3. Bizalmi szintek

| Szint | Név | Feltétel | Mire használható |
|---|---|---|---|
| **T0** | hipotézis | nincs futtatva, vagy ismeretlen a licenc | csak jelölt „ötlet” a promptban, tényként soha |
| **T1** | statikusan rendben | parse/typecheck/lint zöld, futó teszt nincs (pl. CSS, HTML, hálózatos kód) | példa, figyelmeztetéssel |
| **T2** | tesztelt | a saját tesztjei zöldek a sandboxban, az **aktuális** környezetben | few-shot példa, kis kockázatú javaslat |
| **T3** | bizonyított | T2 + független (rejtett vagy tulajdonság-) teszt + ≥ 3 sikeres felhasználás | közvetlen újrahasznosítás |
| **T4** | jóváhagyott | T3 + a felhasználó elfogadta, vagy a saját repójában él | elsőbbség a rangsorban |

**Leminősítés:** főverzió-váltás a környezetben (pl. Node 24 → 26) → újraellenőrzés; bukás → T0 + `fail`;
két egymást követő sikertelen felhasználás → éjszakai újraellenőrzés. A forrás tekintélye (`domainTrust` a
`web/src/autolearn/trust.ts`-ből: 1 / 0,65 / 0,4) csak **előzetes súly** — futtatás nélkül T1 fölé nem emel.

## 4. Visszakeresés: FTS5 + beágyazás + fúzió

```ts
async function findSnippets(q: { text: string; lang: string; symbols: string[]; env: Env }, k = 5) {
  const fts = db.fts(`${q.text} ${q.symbols.join(' ')}`, { lang: q.lang, limit: 30 });  // BM25
  const vec = cosineTopK(await embed(q.text), { lang: q.lang, limit: 30 });            // embeddinggemma
  return rrf([fts, vec], 60)                                   // Reciprocal Rank Fusion: Σ 1/(60 + rang)
    .filter((r) => r.trust >= 1 && !r.supersededBy)
    .map((r) => ({ ...r, score: r.rrf * TRUST_W[r.trust] * usageBoost(r.usage) * envMatch(r.env, q.env) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}
const TRUST_W = [0, 0.5, 0.8, 1.0, 1.1];
const usageBoost = (u: Usage) => 0.7 + 0.6 * ((u.solutionPassed + 1) / (u.usedInSolution + 2)); // Laplace
const envMatch = (s: Env, q: Env) => (sameMajor(s, q) ? 1 : 0.6);
```

- A beágyazás a helyi **embeddinggemma** modellel készül (telepítve, ~0,6 GB). A vektorméretet és a CPU-s
  sebességet **mérni kell**; néhány ezer snippetnél a nyers erős koszinusz-keresés is elég (becslés: ms-os nagyságrend).
- Beágyazás csak beszúráskor és éjszakai kötegben; kérésidőben csak a lekérdezést ágyazzuk be.

## 5. Használat a gondolkodó ciklusban

| Találat | Teendő |
|---|---|
| T3–T4, a feladat lényegében ugyanaz (szignatúra egyezik, magas pontszám) | **újrahasznosítás modell nélkül**: futtatás a feladat tesztjeivel → zöld = kész ([../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md)) |
| T2–T4, hasonló | legfeljebb 2 snippet few-shot példaként a Gondolkodó promptjába (≤ 1500 karakter összesen) |
| T0–T1 | csak „ötletként”, jelölve; a válaszban nem idézzük tényként |
| nincs találat | modell; API-kérdésnél előbb az API-index (8. pont), szükség esetén web ([../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md)) |

Minden felhasználás után `snippet_use` sor (pass/fail) → ez táplálja a `usageBoost`-ot és a leminősítést.

## 6. Migráció a meglévő seedből

| Meglévő | Ma | Átalakítás |
|---|---|---|
| `PROGRAMMING_SNIPPETS` (`programmingCurated.ts`, 45 db `ProgSnippet {tech,title,code,source}`) | eredeti idiómák forrás-URL-lel | `VerifiedSnippet`, `source.kind='curated'`, `license='own'`, kezdetben **T0**. Egyszeri „tesztíró” köteg: futtatható (js/node/python/sql) → teszt + sandbox → T2; nem futtatható (css/html/tailwind/bootstrap, JSX-töredék) → parse → T1 |
| `PROGRAMMING_QA` (53 Q→A) | kétnyelvű rövid válaszok | maradnak Q→A-nak, de kapnak `snippetIds`-t; egy válasz nem mondhat ellent egy T2+ snippetnek |
| `WEB_RECIPES` (`recipes.ts`, 10 recept) | teljes sablonok | `ProjectTemplate` + füstteszt: `node-server` → indítás + `GET /` = 200 a loopbacken; HTML-receptek → parse (T1) |
| `SOURCES` (`sources.ts`, 11 link) | hivatalos doksi-linkek | `DocSource` + kötelező `license` + `storeText` jelző (8. pont) |
| `programming.ingested.ts` (generált) | doksi-darabok forrás-URL-lel | T0/T1 darabok; forrásonként licencellenőrzés a felvételkor |

A migráció közben a **Kritikus** szerep a cím–kód egyezést is ellenőrzi. Már most látszik egy eltérés: a
`'Read JSON from a request'` című snippet valójában fájlból olvas (`readFile('config.json')`) → átnevezés kell.
A hálózatot igénylő snippetek (pl. `requests.get`) a sandboxban nem futtathatók → mockolt teszt vagy T1.

## 7. Projektsablonok

`ProjectTemplate { id, stack, files: {path, code}[], smoke: { cmd, expect: 'exit0' | {http, status} }, trust, source, env }`
— a `smoke` a füstteszt (pl. `GET /` → 200); a bizalmi szabályok ugyanazok, mint a snippeteknél.

## 8. API-dokumentáció index

Cél: a modell ne „találjon ki” API-t. A terv `symbols` listáját a futás előtt az index ellen ellenőrizzük
(létezik-e, és a környezet verziójában elérhető-e — pl. `Array.prototype.toSorted` ES2023-tól).

```ts
interface DocSource { id: string; tech: string; title: string; url: string; license: string;
                      storeText: boolean; fetchedAt?: string; ttlDays: number }
interface ApiDocEntry {
  symbol: string;        // 'fs/promises.readFile', 'pathlib.Path.read_text'
  lang: 'ts' | 'js' | 'py' | 'sql';
  signature: string;     // 'readFile(path, options?): Promise<string | Buffer>'
  since?: string; deprecated?: string;
  summary_hu: string;    // SAJÁT szavakkal (licenc!)
  docSourceId: string; url: string; exampleSnippetId?: string;
}
```

Licencbarát, pontos feltöltés **magából a futtatókörnyezetből**: Pythonnál `inspect.signature` a sandbox
stdlibjén (pontosan a telepített 3.12-re igaz), TS/Node-nál a `lib.*.d.ts` és a `@types/node` deklarációk a
TypeScript compiler API-val. A webes doksi csak a `summary_hu`-hoz és a linkhez kell.

## 9. Karbantartás (éjjel, tétlenségben)

- **Verzióváltás** (Node/Python/TS főverzió): az érintett nyelv T2+ snippetjeinek kötegelt újrafuttatása.
- **Duplikátum:** azonos `code_hash` → összevonás (a használati számlálók összeadódnak); koszinusz > 0,95 → a
  magasabb bizalmú marad, a másik `supersededBy`.
- **Elavulás:** `deprecated` API-t használó snippet → T1-re le, és „frissítendő” feladat a gyakorlósorba ([08](08-gyakorlofeladatok.md)).

## 10. Kész, ha

- a séma és a migráció kész, a 45 kurált snippet betöltve, és ≥ 60 %-uk tesztelve T2-re emelkedett (a többi indokolt T1/T0);
- a `findSnippets` egy 30 kérdéses saját tesztkészleten ≥ 80 %-ban releváns T2+ találatot ad az első 3-ban (célérték);
- a lekérdezés p95-ös ideje a beágyazás nélkül < 200 ms (célérték, mérni kell);
- egy titkot vagy személyes adatot tartalmazó beszúrási kísérletet a tár **elutasít** (teszt fedi).

## Kapcsolódó

- [04-sandbox-kodfuttatas.md](04-sandbox-kodfuttatas.md) · [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [07-sajat-projektekbol-tanulas.md](07-sajat-projektekbol-tanulas.md)
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) · [../05-tanulas/04-tudas-ellenorzese.md](../05-tanulas/04-tudas-ellenorzese.md)
- [../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md) · [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md)
