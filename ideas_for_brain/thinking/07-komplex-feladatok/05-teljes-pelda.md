# Teljes példa: todo REST API (Node + Express + SQLite) tesztekkel

> **Miről szól:** egyetlen kérés teljes útja a gondolkodó cikluson át — emlékezés, megértés, terv,
> minden feladat a bemenetével, checkjével és a két valószerű javítókörrel, a záró kapu, a jelentés és
> amit Auri megjegyez. **Minden időadat becslés** (kódoló modell még nincs telepítve, nem mértük).

## 0. A kérés és a környezet

**Kérés:** „Írj egy Node+Express+SQLite todo REST API-t tesztekkel.”

**Szint és sandbox:** ez **L3** (kis projekt), és `npm`-csomagot használ → csak **S1** sandboxban futhat
(WSL2 + bubblewrap; ma nincs telepítve — [../11-utemterv/03-nyitott-kerdesek.md](../11-utemterv/03-nyitott-kerdesek.md) NK2). A példa tehát a P5-öt mutatja.

**Környezet** (a Windows-gépen ellenőrizve, 2026-11-21; az S1-ben ugyanaz a Node-verzió kell): Node **v24.14.0** —
a beépített `node:sqlite` (`DatabaseSync`) betölthető, de `ExperimentalWarning`-ot ír a stderr-re; a `node:test`
és a `fetch` megvan → **nincs natív fordítás**; az egyetlen külső csomag az `express` (5.x), engedélylistás,
előre letöltött cache-ből, hálózat nélkül (`npm ci --offline`).

**Időbecslés alapja (becslés):** 7B-s kódoló modell ~3 tok/s generálás, ~40 tok/s prefill (nem mért, NK14);
mért viszonyítás: a gemma4:e2b ~6,2 tok/s.

## 1. Emlékezés — 0 LLM-hívás

Keresés a kódtudástárban: `express`, `sqlite`, `rest api`, `node:test`. Első alkalommal az eredmény
**részleges**: van `node` váz-sablon (a `codeProjects.ts` `scaffold()`-jából bővítve) és egy hivatalos
`node:sqlite` dokumentáció-kivonat, de **nincs** ellenőrzött todo-API recept → tovább a megértésre.

## 2. Megértés — 1 hívás (~1,5 perc)

A Gondolkodó a kérésből és egy AC-sablonból elfogadási feltételeket ír; a szabálymotor kiegészíti:

| AC | Feltétel |
|---|---|
| AC1 | 5 végpont: `GET/POST /todos`, `GET/PATCH/DELETE /todos/:id`, JSON |
| AC2 | validáció: `title` kötelező, 1–200 karakter; `done` boolean → különben 400 + hibaforma |
| AC3 | nem létező id → 404; minden 4xx teste `{ error: { code, message } }` |
| AC4 | `npm test` hálózat nélkül, memóriabeli adatbázissal fut |
| AC5 | `npm start` (`PORT`, alap 3000); `GET /health` → 200 |
| AC6 | README a futtatással |

Kérdés **nincs**: az auth, a lapozás és az ID-típus ésszerű alapértelmezéssel eldönthető → ezek
**feltételezésként** kerülnek a jelentésbe ([04-onellenorzes-es-javitas.md](04-onellenorzes-es-javitas.md) 7. pont).

## 3. Terv — 1 hívás (~4,3 perc), `validate()` elsőre 0 hiba

```
F1 váz ─▶ F2 szerződés ─┬─▶ F3 repo-tesztek ─▶ F5 src/repo.js ─┐
                        └─▶ F4 API-tesztek ──────────────────────┴─▶ F6 src/app.js ─▶ F7 src/server.js ─▶ F8 README ─▶ F9 záró kapu
```

Mérföldkövek és kapuk: **M1 Alap** (F1 sablonból, 0 LLM; F2) → szerződés befagyasztva · **M2 Tesztek** (F3, F4)
→ lefutnak és **pirosak** (hiányzó modul, nem szintaxishiba) · **M3 Tárolás** (F5) → `repo.test.js` zöld ·
**M4 HTTP** (F6, F7) → `api.test.js` zöld + smoke · **M5 Lezárás** (F8, F9) → minden teszt + smoke + őr.

## 4. Végrehajtás feladatonként

| Feladat | Be / ki token (becslés) | Idő (becslés) | Check | Eredmény |
|---|---|---|---|---|
| F1 váz | — | ~10 s | `npm ci --offline`, `node --check` | ✅ |
| F2 `src/contract.js` | 600 / 350 | ~2,2 perc | `parse`; befagyasztás (hash) | ✅ 1. próba |
| F3 `test/repo.test.js` (6 teszt) | 900 / 600 | ~3,7 perc | `parse`; piros: `Cannot find module '../src/repo.js'` = várt | ✅ |
| F4 `test/api.test.js` (11 teszt) | 1000 / 800 | ~4,9 perc | `parse`; piros | ✅ |
| F5 `src/repo.js` | 1400 / 500 | ~3,4 perc | repo-tesztek: **5/6** | ⚠ → 1 javítókör (~3,3 perc) → 6/6 ✅ |
| F6 `src/app.js` | 1800 / 800 | ~5,2 perc | API-tesztek: **9/11** | ⚠ → 2 javítókör (~2 × 5,1 perc) → 11/11 ✅ |
| F7 `src/server.js` | 500 / 150 | ~1 perc | smoke: `GET /health` = 200, 5 s-on belül, csak loopback | ✅ |
| F8 `README.md` | 500 / 300 | ~1,9 perc | a README parancsai léteznek a `package.json`-ban | ✅ |
| F9 záró kapu | — | ~10 s | 17/17 teszt, smoke, őr (szerződés-hash, tiltott import, tesztszám) | ✅ |

Az API-tesztek mintája (F4 kimenete, a szerződésből és az AC-kből):

```js
test('POST /todos üres title → 400 + hibaforma', async () => {
  const res = await post('/todos', { title: '' });          // app.listen(0) + fetch, :memory: DB
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error.code, 'invalid_title');
});
```

## 5. A két javítókör közelről

**F5 — SQLite és a boolean.** A kivonat (a stderr `ExperimentalWarning`-ját a kivonat-készítő zajként
kiszűri, különben a modell azt próbálná „javítani”):

```
check: test  failing: 1/6  first: "update sets done"  expected: true  actual: 1
location: src/repo.js:31   signature: strictEqual|repo.update|number!=boolean
```

A `node:sqlite` a boolean-t 0/1 egészként adja vissza (a gépen ellenőrizve: `{"b":1}`). Javítás egy
sorban, a tárolási rétegben:

```js
const toTodo = (r) => r && { id: r.id, title: r.title, done: r.done === 1, createdAt: r.created_at };
```

**F6 — Express és a kérés-törzs.** 1. kör: két teszt 500-at kap 400 helyett, közös ok:
`TypeError: Cannot read properties of undefined (reading 'title')` → hiányzik az `app.use(express.json())`.
A javítás után **új aláírás** jön (haladás, nem körbejárás): az érvénytelen JSON már 400, de a test
HTML, nem a szerződés hibaformája. 2. kör: hibakezelő middleware:

```js
app.use((err, req, res, next) => {
  if (err.type === 'entity.parse.failed')
    return res.status(400).json({ error: { code: 'bad_json', message: 'Érvénytelen JSON' } });
  next(err);
});
```

## 6. Lezárás: Kritikus, jelentés

A Kritikus a végén egyben fut (~2,4 perc): egy `low` megjegyzés — „a `GET /todos` nem lapoz” →
**javaslat**, nem kapu, nem csinálja meg. A jelentés a naplóból készül:

```
✅ Kész: todo REST API (Node 24 + Express 5 + node:sqlite) — 17/17 teszt zöld, smoke rendben.
Feltételezések: nincs auth, nincs lapozás, egész számú ID, adatbázis: data/todos.db.
Javítások: 3 kör (SQLite 0/1 → boolean; express.json; JSON-hibaforma).
Idő: ~47 perc (LLM ~45 perc). Munkaterület: sandbox/runs/run-0007 (exportálható .zip-ként).
Javaslat (nem csináltam meg): lapozás a GET /todos-on.
```

**A munkaterület** (saját git-repó, feladatonként egy commit): `package.json`, `.gitignore`, `README.md`,
`src/{contract,repo,app,server}.js`, `test/{repo,api}.test.js`; mellette a napló (`data/runs/run-0007/journal.jsonl`), illusztráció:

```jsonl
{"type":"check","task":"F5","attempt":1,"check":"test:test/repo.test.js","ok":false,"digest":"strictEqual|repo.update|number!=boolean"}
{"type":"check","task":"F5","attempt":2,"check":"test:test/repo.test.js","ok":true}
{"type":"checkpoint","task":"F5","commit":"a1b2c3d"}
```

## 7. Amit megjegyez — és amit nem

| Mit | Hova | Bizalom |
|---|---|---|
| a teljes megoldás + 17 teszt | `VerifiedSnippet`-ek (fájlonként) | T2 (lefuttatva); T3 rejtett teszt + 3 bevált újrahasználat után |
| recept `rest-api-node-sqlite` (terv + szerződés-sablon, paraméter: entitás, mezők) | receptek | T2; minden sikeres újrahasználat emeli |
| 2 hibaminta: „node:sqlite: boolean → 0/1, a tárolási rétegben konvertálj”; „Express: `req.body` csak `express.json()` után; JSON-hiba → saját hibaforma” | `ErrorPattern` | a javítás után zöld → `worked` +1 |
| idők, körök száma, modell, token | fejlődési napló | mérés |
| **nem:** a Kritikus nem igazolt megjegyzése, gépspecifikus útvonalak, bármilyen személyes adat | — | — |

## 8. Időösszesítő (becslés)

| Rész | Idő |
|---|---|
| megértés + terv | ~6 perc |
| első generálások (F2–F8) | ~22 perc |
| javítókörök (1 + 2) | ~13,5 perc |
| Kritikus + tanulság-jegyzet | ~4 perc |
| sandbox-futtatások + egy hideg modellbetöltés (a telepítetteknél mérve 18,5–38,3 s; a kódolóé mérni kell) | ~1–2 perc |
| **Összesen** | **~47 perc** egy 7B-s kódoló modellel; a mért e2b-sebességgel kb. fele, de valószínűleg több javítókörrel |

Ez hosszú, ezért: kérésre indul (`TASK`, nem háttérmunka), a HUD-on követhető, szüneteltethető, a `VOICE` mindig megelőzi; ha a 60 perces alapkeret elfogyna → szünet + kérdés.

## 9. A második alkalom — itt látszik az „okosodás”

Következő kérés: „Írj egy notes API-t.” Most a recept talál → a terv **0 LLM-hívás**, a szerződés és a
tesztek a receptből paraméterezve, a hibaminták már a prompt elején → várhatóan 0 javítókör.
Várható idő: **~47 → ~20 perc** (becslés, **mérni kell** — ez a P5 egyik mérőszáma).

## 10. Kész, ha (ez a példa a P5 elfogadási tesztje)

- A teljes példa emberi beavatkozás nélkül lefut, a 17/17 teszt zöld, a jelentés minden állítása a naplóra mutat.
- 5 futásból legalább 3 sikeres (célérték, becslés); a medián idő és a körök száma a fejlődési naplóban.
- A második (notes) kérés a receptet használja, és a mért idő kisebb, mint az elsőé.

## Kapcsolódó

- [01-feladatbontas.md](01-feladatbontas.md) · [02-terv-vegrehajtas-ellenorzes.md](02-terv-vegrehajtas-ellenorzes.md) · [03-tobbfajlos-projektek.md](03-tobbfajlos-projektek.md) · [04-onellenorzes-es-javitas.md](04-onellenorzes-es-javitas.md)
- [../06-programozas/04-sandbox-kodfuttatas.md](../06-programozas/04-sandbox-kodfuttatas.md) · [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md) (receptek, hibaminták) · [../06-programozas/09-meres-es-benchmark.md](../06-programozas/09-meres-es-benchmark.md)
- [../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md](../10-meres-es-fejlodes/03-fejlodesi-naplo-sablon.md) · [../11-utemterv/01-fazisok.md](../11-utemterv/01-fazisok.md) (P5)
