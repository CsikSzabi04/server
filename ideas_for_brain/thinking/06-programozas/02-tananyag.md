# Tananyag — mit, milyen sorrendben, milyen forrásból

> **Miről szól:** a programozási tananyag mint **témagráf**: nyelvenkénti és keresztmetszeti témák
> előfeltételekkel, a források **licencével**, és az ütemező, ami eldönti, mit tanuljon Auri a következő
> szabad idősávban. Egy téma csak akkor „megtanult”, ha a gyakorlófeladatai mérhetően mennek.

## 1. Elvek

1. **Téma = gyakorolható + ellenőrizhető egység.** Minden témához tartozik legalább egy feladatcsalád ([08](08-gyakorlofeladatok.md));
   amit nem lehet teszttel gyakorolni, az csak tudáskártya.
2. **Előfeltételek sorrendje kötelező.** Async előtt függvények és hibák; React előtt TS-típusok és modulok.
3. **A felhasználó stackje előbbre sorol** (TS/React/Node, Python, SQL) — a súlyt a saját repók adják ([07](07-sajat-projektekbol-tanulas.md)).
4. **Licenc nélkül nincs tárolás.** Ismeretlen licencű forrásból csak link és saját szavas összefoglaló kerülhet be
   ([../05-tanulas/05-mit-nem-szabad-megtanulni.md](../05-tanulas/05-mit-nem-szabad-megtanulni.md)).

## 2. A témagráf adatszerkezete

```ts
interface Topic {
  id: string;                  // 'ts.async.promise-all'
  lang: 'ts' | 'py' | 'sql' | 'x';   // x = keresztmetszeti
  title_hu: string;
  level: 0 | 1 | 2 | 3 | 4;    // a létra szintje (01)
  prereqs: string[];           // topic id-k — körmentes gráf (ellenőrizni betöltéskor!)
  sources: string[];           // DocSource id-k (03), mind licenccel
  exerciseFamilies: string[];  // feladatcsaládok (08)
  mastery: {
    attempts: number; passRate: number;   // az utolsó 10 próbálkozásból
    sessions: number;                     // hány külön alkalommal gyakorolta
    due?: string;                         // következő ismétlés (05-tanulas/03)
  };
}
const mastered = (t: Topic) =>
  t.mastery.attempts >= 10 && t.mastery.passRate >= 0.8 && t.mastery.sessions >= 2;
```

## 3. TypeScript / JavaScript + Node (sorrendben)

1. `ts.basics` — változók, primitív típusok, vezérlési szerkezetek (L0)
2. `ts.functions` — függvények, nyílfüggvény, alapértelmezett és rest paraméter, closure (L0–L1)
3. `ts.collections` — tömb és objektum, `map`/`filter`/`reduce`, destrukturálás, spread, `Map`/`Set` (L1)
4. `ts.strings` — template literal, regex, Unicode és ékezetek (`normalize('NFD')`) (L1)
5. `ts.errors` — `try/catch`, saját `Error`, `unknown` szűkítése (L1)
6. `ts.types` — unió, szűkítés, generikusok, utility típusok, `satisfies` (L1–L2)
7. `ts.modules` — ESM `import`/`export`, `import type` (a Node típuslecsupaszítása miatt fontos) (L1)
8. `ts.classes` — osztály, interfész, kompozíció öröklés helyett (L2)
9. `ts.async` — Promise, `async/await`, `Promise.all`/`allSettled`, időzítők, `AbortController`, injektált óra (L2)
10. `node.io` — `fs/promises`, `path`, `process`, streamek alapjai; a sandboxban csak a futási mappán belül (L2)
11. `node.http` — HTTP-szerver, Express routing, middleware, bemenet-validáció, hibakezelő middleware (L2–L3)
12. `ts.testing` — `node:test` + `node:assert`, táblázatos tesztek, mock, `fast-check` (L1-től folyamatosan)
13. `react.*` — komponens, props, state, effect, listák kulccsal, kontrollált űrlap, saját hook, context,
    adatlekérési minták; komponensteszt csak ha a sandboxban van DOM-emuláció (L2–L3)

## 4. Python (sorrendben)

1. `py.basics` (L0) · 2. `py.functions` — `*args`/`**kwargs`, a módosítható alapérték csapdája (L0–L1)
3. `py.collections` — list/dict/set/tuple, comprehension (L1) · 4. `py.strings` — f-string, `unicodedata` (L1)
5. `py.errors` — kivételek, saját kivételosztály (L1) · 6. `py.typing` — type hint, `dataclass`, `Protocol` (L1–L2)
7. `py.iter` — iterátor, generátor, `itertools` (L2) · 8. `py.io` — `pathlib`, `json`, `csv`, **`encoding="utf-8"`** (L2)
9. `py.oop` — osztályok, dunder metódusok, kompozíció (L2) · 10. `py.testing` — pytest, fixture, `parametrize`, Hypothesis (L1-től)
11. `py.async` — `asyncio` alapok (a Jarvis is erre épül) (L2) · 12. `py.sqlite` — `sqlite3`, paraméterezett lekérdezés (L2)
13. `py.http` — `httpx`-kliens **mockolt** transzporttal (a sandboxban nincs hálózat) (L2–L3)

## 5. SQL (SQLite-on futtatva)

`sql.select` (SELECT/WHERE/ORDER BY/LIMIT) → `sql.aggregate` (GROUP BY/HAVING) → `sql.join` (INNER/LEFT) →
`sql.subquery` (al-lekérdezés, CTE) → `sql.window` (ablakfüggvények) → `sql.ddl` (kényszerek, index) →
`sql.tx` (tranzakciók) → `sql.null` (NULL-szemantika) → `sql.params` (paraméterezés, SQL-injekció).
Dialektuskártyák (csak tudás, amíg nincs DB-konténer): `sql.pg` (PostgreSQL/Supabase, RLS), `sql.mysql`, `sql.oracle`.

## 6. Keresztmetszeti témák (`x.*`)

| Téma | Tartalom | Mikortól |
|---|---|---|
| `x.algo` | O-jelölés, rendezés, bináris keresés, két mutató, hash, rekurzió, BFS/DFS, egyszerű DP | L1 |
| `x.ds` | tömb, Map/Set, verem/sor, kupac, fa, gráf | L1 |
| `x.testing` | egység-, táblázatos, tulajdonságalapú teszt, mock, tesztpiramis | L1 |
| `x.debug` | a [06](06-hibakereses.md) módszere, hibaüzenetek olvasása | L1 |
| `x.git` | commit, branch, diff, merge-konfliktus, `bisect` — egy **eldobható** sandbox-repóban | L2 |
| `x.http` | metódusok, státuszkódok, fejlécek, JSON, idempotencia, CORS, hitelesítés alapjai | L2 |
| `x.async` | párhuzamossági limit, újrapróbálás backoff-fal, megszakítás, versenyhelyzet | L2 |
| `x.security` | SQL-injekció, XSS, titokkezelés, bemenet-validáció | L2 |
| `x.design` | tiszta függvények, függőséginjektálás, rétegzett hibakezelés | L2–L3 |

## 7. Később (amikor a sandbox futtatni tudja)

Java, Kotlin, PHP, MySQL, Oracle, Docker: addig csak `L0` tudáskártyák a meglévő seedből
(`web/src/brain/seed/programmingCurated.ts`), legfeljebb T1 bizalommal. A futtatókörnyezet bővítése nyitott kérdés
([../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md)).

## 8. Források és licencek

| Forrás | Mire | Licenc (ellenőrizendő a felvételkor) | Hogyan használjuk |
|---|---|---|---|
| MDN Web Docs | JS, HTML, CSS, HTTP | próza: CC BY-SA 2.5; kódpéldák (2010.08.20. után): CC0 | kódpélda tárolható; próza saját szavakkal + link |
| Node.js dokumentáció (`nodejs/node`) | Node API | MIT | API-index ([03](03-kod-tudasbazis.md)), rövid idézet + link |
| TypeScript Handbook | TS | tartalom CC BY 4.0, kód MIT (**ellenőrizni kell**) | összefoglaló + link |
| react.dev | React | CC BY 4.0 (**ellenőrizni kell**) | összefoglaló + link |
| docs.python.org | Python | PSF; a dokumentáció kódpéldái 0BSD is (3.8.6 óta) | kódpélda tárolható |
| SQLite / PostgreSQL docs | SQL | közkincs / PostgreSQL License | tárolható, forrással |
| PHP manual | PHP | CC BY 3.0 | forrásmegjelöléssel |
| Oracle Java és MySQL docs | Java, MySQL | szerzői jogvédett, korlátozó | **csak link**, szöveget nem tárolunk |
| Exercism `problem-specifications` | feladatok + kanonikus tesztadat | MIT | feladatforrás ([08](08-gyakorlofeladatok.md)) |
| TheAlgorithms (Python, TypeScript) | algoritmus-referenciák | MIT | referencia-megoldás a differenciális teszthez |
| Stack Overflow | hibák, trükkök | CC BY-SA (4.0; régebbiek 2.5/3.0) | csak hivatkozással és licencmezővel |
| Pro Git könyv | git | CC BY-NC-SA 3.0 | olvasás + saját összefoglaló, szó szerint nem |
| Project Euler | matematikai algoritmusok | CC BY-NC-SA 4.0 | csak belső gyakorlás, megoldás nem publikus |
| LeetCode és hasonló zárt oldalak | — | zárt | **tilos** |
| HumanEval / MBPP | csak „public-sanity” mérés | MIT / CC BY 4.0 | **soha nem tananyag** (szennyezés, [09](09-meres-es-benchmark.md)) |

## 9. Ütemezés: mit tanuljon legközelebb

```ts
function nextTopic(topics: Topic[], now: Date): Topic | null {
  const ready = topics.filter((t) => runnable(t.lang) && t.prereqs.every((p) => mastered(byId(p))));
  const due = ready.filter((t) => t.mastery.due && new Date(t.mastery.due) <= now);
  if (due.length) return minBy(due, (t) => t.mastery.passRate);       // 1. esedékes ismétlés
  const open = ready.filter((t) => !mastered(t));
  return maxBy(open, (t) =>                                              // 2. új/gyenge téma
    0.5 * (1 - t.mastery.passRate) + 0.3 * stackWeight(t) + 0.2 * unlocks(t) / maxUnlocks);
}
// stackWeight: a téma gyakorisága a saját repókban (07), 0..1 · unlocks: hány témát nyit meg
```

Egy **tanulási egység** egy témára (éjjel vagy tétlenségben, [../05-tanulas/02-ejszakai-onallo-tanulas.md](../05-tanulas/02-ejszakai-onallo-tanulas.md)):
1. a licencben engedett forrásrészlet beolvasása (cache-ből, ha friss);
2. a **Tanár** szerep 3–5 magyar kulcspontot ír ([../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md](../04-nyelv-es-mondatalkotas/03-magyarazas-es-tanitas.md));
3. 3 gyakorlófeladat a téma családjaiból ([08](08-gyakorlofeladatok.md)) a TDD-ciklussal ([05](05-tesztvezerelt-gondolkodas.md));
4. a zöld megoldások ellenőrzött snippetként a tudástárba ([03](03-kod-tudasbazis.md));
5. a `mastery` frissítése és a következő ismétlés dátuma ([../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md)).

## 10. Kész, ha

- a témagráf egy verziózott adatfájlban van (≥ 60 téma), a betöltő **körmentességet** és létező előfeltételeket ellenőriz;
- minden témának van ≥ 1 licenccel felvett forrása és ≥ 1 feladatcsaládja;
- a `nextTopic` determinisztikus (azonos állapot → azonos téma), és egységtesztek fedik az esedékes/új/blokkolt eseteket;
- a heti jelentés témánként mutatja a `passRate`-et és a megtanult témák számát.

## Kapcsolódó

- [01-cel-es-szintek.md](01-cel-es-szintek.md) · [03-kod-tudasbazis.md](03-kod-tudasbazis.md) · [08-gyakorlofeladatok.md](08-gyakorlofeladatok.md)
- [../05-tanulas/01-tanulasi-forrasok.md](../05-tanulas/01-tanulasi-forrasok.md) · [../05-tanulas/03-ismetles-felejtes-konszolidacio.md](../05-tanulas/03-ismetles-felejtes-konszolidacio.md)
- [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) · [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md)
