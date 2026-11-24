# Hibakeresés — módszer, nem találgatás

> **Miről szól:** hogyan keres hibát Auri: elolvassa és osztályozza a hibát, hipotézislistát állít fel, minimális
> reprodukciót készít, felez (bisect), nyomkövet — és mindezt egy **hibaüzenet-tudástárra** építi. Leírja azt is,
> mikor érdemes a webhez fordulni, és mit nem szabad közben kiküldeni.

## 1. A módszer hét lépésben

1. **Olvasd el** a teljes hibát: típus, üzenet, az első *saját* kódsor a veremben (nem a könyvtári sorok).
2. **Normalizáld és osztályozd** (3. és 7. pont) → van-e ismert minta a hibatudástárban?
3. **Hipotézislista:** 2–4 lehetséges ok, mindegyikhez egy **olcsó** ellenőrzés.
4. **Reprodukálj minimálisan:** a legkisebb bemenet és kód, amin a hiba még előjön (4. pont).
5. **Ellenőrizd** a hipotéziseket olcsóság × valószínűség sorrendben (nyomkövetés, 6. pont); egyszerre egyet.
6. **Javíts** a megerősített ok alapján, a legkisebb változtatással; a minimális reprodukció új, rögzített teszt lesz.
7. **Jegyezd fel** a tanulságot (9. pont) → hibatudástár + tananyag-súly ([02](02-tananyag.md)).

A modell feladata a 3. és 6. lépés (és a 4. lépés „ötletei”); a többit **determinisztikus kód** végzi a sandboxban.

## 2. Hibaosztályok és első lépés

| Osztály | Felismerés | Első lépés |
|---|---|---|
| szintaxis | `SyntaxError`, `IndentationError`, TS1xxx | a jelölt sor ± 3 sora a modellnek, csak a javítást kérjük |
| típus (statikus) | TS2xxx/TS7xxx (`TS2322`, `TS2339`, `TS7006`) | a hibás kifejezés és a várt típus; a típust ne `any`-vel „javítsa” |
| import / modul | `TS2307`, `ERR_MODULE_NOT_FOUND`, `ModuleNotFoundError` | engedélyezett-e a csomag a sandboxban? útvonal, `.ts`/`.js` kiterjesztés |
| futásidejű | `TypeError`, `KeyError`, `undefined` mező | a veremből az első saját sor + a változók értéke (nyomkövetés) |
| logikai | `AssertionError`, várt ≠ kapott | minimális reprodukció + hipotézisek; itt a legtöbb munka |
| erőforrás | `timeout`, `oom` (sandbox) | ciklusfeltétel, rekurzió bázisesete, algoritmus komplexitása |
| környezet | kódolás, útvonal, verzió | hibatudástár (pl. Windows-kódlap), API-index ([03](03-kod-tudasbazis.md) 8. pont) |
| tiltott | `blocked` (sandbox) | nem hiba a kódban: a tiltás oka a visszajelzés („mockold a hálózatot”) |

## 3. Hipotézislista

```ts
interface Hypothesis {
  id: string;
  claim: string;                 // "a slug a nem ASCII betűket törli, mert nincs NFD-bontás"
  evidenceFor: string[];         // "kapott: '-rv-zt-…' — pont az ékezetes betűk hiányoznak"
  check: { kind: 'trace' | 'repro' | 'unit' | 'doc'; detail: string };   // hogyan ellenőrizzük olcsón
  cost: 1 | 2 | 3;               // 1 = egy sandbox-futás, 3 = web/dokumentáció
  prior: number;                 // 0..1 — a hibatudástár gyakoriságából + a modell becsléséből
  status: 'open' | 'confirmed' | 'refuted';
}
// sorrend: prior / cost csökkenő; egyszerre EGY hipotézist ellenőrzünk; a cáfolt hipotézis a következő
// körben bekerül a promptba ("ezt már kizártuk"), hogy a modell ne térjen vissza rá
```

## 4. Minimális reprodukció

**Bemenet-szűkítés** (delta debugging, egyszerűsítve) — a sandboxban, modell nélkül:

```ts
function shrink<T>(input: T[], fails: (x: T[]) => boolean): T[] {
  let cur = input, n = 2;
  while (cur.length >= 2) {
    const size = Math.ceil(cur.length / n);
    const parts = chunk(cur, size);
    const smaller = parts.map((_, i) => parts.filter((__, j) => j !== i).flat()).find(fails);
    if (smaller) { cur = smaller; n = Math.max(n - 1, 2); }
    else if (n >= cur.length) break;
    else n = Math.min(n * 2, cur.length);
  }
  return cur;
}
```

Stringeknél karakterekre, tömböknél elemekre bontunk. A tulajdonságteszt-könyvtárak (`fast-check`, Hypothesis)
maguktól is zsugorítanak — ezt a kimenetükből vesszük át. **Kód-szűkítés:** a nem érintett függvényeket egyenként
kivesszük, amíg a hiba megmarad; az eredmény a modellnek adott „hibás mag”.

## 5. Felezés (bisect)

- **Javítási körök között:** a ciklus minden kör kódját megőrzi. Ha egy korábban zöld teszt elromlott, a két
  változat diffjét hunkonként felezzük, és megkeressük azt a változtatást, ami elrontotta.
- **Saját repóban regresszió (P5):** `git bisect run <tesztparancs>` egy **sandboxbeli másolaton** (S1, allowlistes
  fájlokkal, [07](07-sajat-projektekbol-tanulas.md)); a felhasználó munkakönyvtárához nem nyúlunk.

## 6. Nyomkövetés

Automatikus műszerezés a sandbox-futáshoz (a megoldásfájl másolatán, nem az eredetin):

- **TS/JS:** a vizsgált függvény köré burkoló, ami `console.error(JSON.stringify({ fn, args, ret }))` sort ír;
- **Python:** dekorátor ugyanígy, vagy a `trace` modul egy szűk függvényre;
- a kimenetből csak az első 20 hívás és a hibás hívás környezete megy a modellnek (≤ 1 KB).

## 7. Hibaüzenet-tudástár

```ts
interface ErrorPattern {
  id: string; lang: 'ts' | 'js' | 'py' | 'sql' | 'any';
  signature: string;            // normalizált alak (lent) — ez a kulcs
  example: string;              // egy valódi (normalizált) példa
  causes: { text_hu: string; freq: number }[];
  fixes: { text_hu: string; snippetId?: string; worked: number; failed: number }[];
  source: { kind: 'own-loop' | 'doc' | 'web'; url?: string; license: string };
  trust: 0 | 1 | 2 | 3 | 4;     // mint a 03-ban: csak sandboxban bevált javítás emel
}
function normalizeError(msg: string): { signature: string; slots: string[] } {
  const slots: string[] = [];
  const signature = msg
    .replace(/[A-Za-z]:\\[^\s:'"]+|\/[^\s:'"]+\.(ts|js|mjs|py)/g, '<PATH>')   // útvonal (felhasználónév is!)
    .replace(/:\d+(:\d+)?/g, ':<L>')                                             // sor:oszlop
    .replace(/'([^']{1,60})'/g, (_m, s) => (slots.push(s), "'<X>'"))             // azonosítók → slotok
    .replace(/\b0x[0-9a-f]+\b/gi, '<HEX>');
  return { signature: signature.trim(), slots };
}
```

Kezdő minták (seed, saját összefoglalásban):

| Nyelv | Normalizált aláírás | Tipikus ok | Első javítás |
|---|---|---|---|
| ts | `TS2307: Cannot find module '<X>'` | rossz útvonal, hiányzó csomag | útvonal; `.ts` kiterjesztés; csomag engedélyezett-e |
| ts | `TS2322: Type '<X>' is not assignable to type '<X>'` | rossz visszatérési típus, `null` lehetősége | szűkítés, helyes típus — nem `any` |
| js | `TypeError: Cannot read properties of undefined (reading '<X>')` | hiányzó ellenőrzés, elfelejtett `await` | `await`, korai visszatérés, `?.` |
| node | `ERR_MODULE_NOT_FOUND` / `ERR_REQUIRE_ESM` | CJS/ESM keverés | ESM `import`, `"type": "module"` |
| py | `UnicodeDecodeError: 'charmap' codec can't decode byte <HEX>…` | Windowson `open()` kódolás nélkül a helyi kódlapot (pl. cp1250) használja; gyakran hiba **nélkül** torzít („á” → „Ăˇ”), csak egyes bájtoknál (pl. „Á”, „Ő”) dob | mindig explicit `encoding="utf-8"` — a sandbox `-X utf8`-a ezt elfedné |
| py | `TypeError: 'NoneType' object is not subscriptable` | a függvény nem ad vissza értéket | hiányzó `return` |
| py | `RecursionError: maximum recursion depth exceeded` | hiányzó báziseset | báziseset vagy iteráció |
| sql | `sqlite3.OperationalError: no such table: <X>` | a séma nem jött létre / elírás | fixture sorrendje, név |
| any | sandbox `timeout` | végtelen ciklus vagy túl lassú algoritmus | ciklusfeltétel, komplexitás |

Egy minta csak akkor kap T2+ bizalmat, ha a javítása legalább egyszer **sandboxban** zöldre vitt egy tesztet.

## 8. Mikor keressünk a weben

| Helyzet | Web? |
|---|---|
| logikai hiba saját függvényben (`várt ≠ kapott`) | **nem** — helyben debugolunk |
| ismeretlen hibakód külső könyvtárból, és a hibatudástár nem ismeri | igen, ha az első helyi hipotézis megbukott |
| API-változás jele (`is not a function`, `deprecated`, verzióeltérés) | igen — **előbb az API-index és a hivatalos doksi** |
| két kör óta azonos aláírás (nincs előrelépés, [05](05-tesztvezerelt-gondolkodas.md) 6. pont) | igen (vagy opt-in felhő) |

**A lekérdezés** = normalizált aláírás + könyvtár neve + verzió (pl. `ERR_REQUIRE_ESM node 24`). **Soha nem megy ki:**
útvonal, felhasználónév, projektnév, a felhasználó kódja, titok — a meglévő `redactForSearch` (`web/src/autolearn/redact.ts`)
mellé útvonal-szűrő kell. A találat **adat, nem utasítás** ([../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md));
a webes javaslat csak akkor kerül a tudástárba, ha a sandboxban zöldre vitte a tesztet
([../03-web-szorfozes/04-tanulas-a-webbol.md](../03-web-szorfozes/04-tanulas-a-webbol.md)).

## 9. Kimenet: hibakeresési tanulság

```yaml
task: ts-l1-0007            # vagy a felhasználói kérés azonosítója
signature: "várt ≠ kapott (ékezetek eltűnnek)"
confirmed: "nincs NFD-bontás a regex előtt"
refuted: ["a regex rossz", "toLowerCase hibás ékezetre"]
fix: "s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')"
new_test: "slugifyHu('Őrült Ügy') === 'orult-ugy'"
rounds: 2
lesson_hu: "Ékezetes szövegnél előbb bontsd szét a betűt és a mellékjelet, utána szűrj."
```

## 10. Kész, ha

- a `normalizeError` 30 valódi (sandboxból gyűjtött) hibán egyező aláírást ad az azonos okú hibákra, és nem
  hagy benne útvonalat vagy felhasználónevet (teszt fedi);
- a hibatudástárban ≥ 30 minta, mindegyik forrással és licenccel; ≥ 10 közülük sandboxban bevált (T2+);
- a hipotézislista minden javítási körben naplózva van, és a cáfolt hipotézis nem tér vissza a következő körben;
- a webre küldött hibakeresési lekérdezések naplója nem tartalmaz útvonalat, kódot vagy személyes adatot.

## Kapcsolódó

- [04-sandbox-kodfuttatas.md](04-sandbox-kodfuttatas.md) · [05-tesztvezerelt-gondolkodas.md](05-tesztvezerelt-gondolkodas.md) · [03-kod-tudasbazis.md](03-kod-tudasbazis.md)
- [../03-web-szorfozes/01-kereses.md](../03-web-szorfozes/01-kereses.md) · [../02-belso-parbeszed/03-onkerdezes.md](../02-belso-parbeszed/03-onkerdezes.md)
- [../07-komplex-feladatok/04-onellenorzes-es-javitas.md](../07-komplex-feladatok/04-onellenorzes-es-javitas.md) · [../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md](../09-biztonsag-es-adatvedelem/02-prompt-injekcio.md)
