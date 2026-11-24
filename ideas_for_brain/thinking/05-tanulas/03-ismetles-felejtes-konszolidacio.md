# Ismétlés, felejtés, konszolidáció — friss és tiszta tudás

> **Miről szól:** hogyan marad a tudástár igaz és rendezett: időzített újraellenőrzés (spaced
> repetition gépi tudásra), éjszakai konszolidáció („álom-fázis”), deduplikálás, felejtés és
> archiválás, ellentmondások kezelése és verzióhoz kötött tudás (pl. React 18 vs 19). Fázis: **P4**.

## 1. A tudáselem — közös séma a 04-es fájllal

A végleges tárolási séma: [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md). Ehhez a fájlhoz ennyi kell:

```ts
type KStatus = 'hypothesis' | 'verified' | 'contested' | 'stale' | 'refuted' | 'archived'; // hypothesis = karantén

interface KnowledgeItem {
  id: string;
  kind: 'fact' | 'snippet' | 'api-note' | 'lesson' | 'error-fix';
  topic: string;                    // 'react/rendering'
  text: string;                     // állítás vagy kód (+ tesztek, ha snippet)
  scope?: { lib: string; range: string; checkedWith?: string }; // 'react', '>=19', '19.0.0'
  sources: SourceRef[];             // url/fájl + domainTrust + license + fetchedAt
  evidence: Evidence[];             // milyen ellenőrzésen ment át (04-es fájl)
  confidence: number;               // 0..1 — igaz-e
  strength: number;                 // hasznosság — használatkor nő, idővel csökken
  status: KStatus;
  review: { reps: number; ease: number; intervalDays: number; lapses: number; nextReviewAt: string };
  ttlDays: number;                  // trust.ts ttlDaysForQuery: 3 nap (változékony) / 180 nap
  contradicts?: string[]; supersedes?: string[];
  history: { at: string; change: string }[];   // semmi nem íródik felül csendben
}
```

## 2. Két külön óra: érvényesség és hasznosság

| | Érvényesség — igaz-e még? | Hasznosság — kell-e még? |
|---|---|---|
| Mérője | TTL, verzió, az ismétlés eredménye | `strength`: használat, sikeres feladat |
| Ha lejár | újraellenőrzés → rendben / `stale` / `contested` | archiválás (nem törlés) |
| Példa | „a legújabb React a 19-es” — változékony, 3 napos TTL | egy soha nem használt jQuery-snippet |

## 3. Ismétlés — embernél memorizálás, itt újraellenőrzés

| Fajta | Mit jelent az „ismétlés” | Kell modell? |
|---|---|---|
| `snippet` | a tárolt tesztek újrafuttatása a sandboxban, az aktuális lib-verzióval | nem |
| `error-fix` | a hibás és a javított példa újrafuttatása: a hiba még ugyanúgy jön, a javítás még zöld | nem |
| `api-note` | a forrás vagy a changelog újraolvasása; ha lehet, futtatható állítás | ritkán |
| `fact` | zárt könyves kvíz és összevetés ([04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)) | igen, röviden |
| `lesson` | a napló alapján: előfordult-e újra a hiba, és a tanulság tényleg segített-e | nem |

Ütemező (az SM-2 algoritmus egyszerűsítése; kezdő `ease` 2,5, a többi érték **becslés**):

```ts
function scheduleNext(r: Review, outcome: 'pass' | 'partial' | 'fail'): Review {
  if (outcome === 'fail')
    return { reps: 0, ease: Math.max(1.3, r.ease - 0.2), intervalDays: 1,
             lapses: r.lapses + 1, nextReviewAt: addDays(1) };
  const reps = r.reps + 1;
  const raw = outcome === 'partial' ? Math.max(1, r.intervalDays * 1.2)
            : reps === 1 ? 1 : reps === 2 ? 4 : r.intervalDays * r.ease;
  const intervalDays = Math.min(180, Math.round(raw));        // 180 = a trust.ts hosszú TTL-je
  const ease = outcome === 'partial' ? Math.max(1.3, r.ease - 0.15) : Math.min(2.8, r.ease + 0.05);
  return { reps, ease, intervalDays, lapses: r.lapses, nextReviewAt: addDays(intervalDays) };
}
```

Következmények: `fail` → `confidence × 0,6`; `lapses ≥ 3` → `contested` és ellenőrzési sor.
Éjszakánként legfeljebb 30–60 ismétlés (becslés, mérni kell) — előbb a modell nélküliek, mert
azok olcsók, és napközbeni „könnyű” ablakban is futhatnak ([02-ejszakai-onallo-tanulas.md](02-ejszakai-onallo-tanulas.md)).

## 4. Konszolidáció („álom-fázis”)

A tanulós éjszaka végén vagy hosszabb tétlenség után (a Jarvis `idle_tick` álom-fázisának mintájára):

1. **Gyűjtés** — a nap epizódjai: feladatnaplók, kudarcok, új jelöltek.
2. **Deduplikálás** — 5. pont.
3. **Összevonás** — legalább 3 hasonló `error-fix` → egy `lesson` jelölt, ami hivatkozik a 3 esetre
   (pl. „asyncio: az `await` nélkül hívott coroutine nem fut le”). A tanulság is ellenőrzésre megy.
4. **Kapcsolatok** — melyik tudás melyikkel együtt kellett egy feladathoz (témagráf élei).
5. **Ellentmondás-keresés** — 7. pont.
6. **Tananyag-javaslat** — ismétlődő hiányokból új témák a sorba.
7. **Jelentés** — a napi tanulási jelentésbe.

Modell csak a 3. és a 6. lépéshez kell (rövid hívások); a többi determinisztikus.

## 5. Deduplikálás

| Szint | Módszer | Küszöb | Honnan |
|---|---|---|---|
| Pontos | normalizált szöveg hash-e | egyezés | — |
| Közeli szöveg | Jaccard (`textSimilar`) | ≥ 0,82 | `web/src/autolearn/dedup.ts` |
| Jelentés | embedding-koszinusz (`embeddinggemma`) | ≥ 0,9 | a Jarvis álom-fázis terve |
| Kód | kommentek és whitespace nélküli token-hash; azonos tesztek | egyezés | javaslat (mérni kell) |

Összevonáskor a nagyobb `confidence` marad elsődleges; a `sources` és az `evidence` egyesül; a
`history`-ba bekerül, mi olvadt bele. **Eltérő `scope` soha nem duplikátum** (a React 18 és a
React 19 jegyzete két külön elem).

## 6. Felejtés és archiválás

- Csökkenés: `strength ← strength × 0,5^(használat nélküli napok / felezési idő)`. Felezési idő
  (becslés): `fact` 90 nap, `api-note` 180 nap, `snippet` és `lesson` 365 nap.
- Használat: sikeres válaszban vagy zöld feladatban +1; ha a használata kudarchoz vezetett, −1 és
  ismétlés esedékessé válik.
- **Archiválás**, ha `strength < 0,1` és 180 napja nem használtuk: kikerül a visszakeresésből, de
  megmarad (okkal), és visszaállítható.
- **Valódi törlés** csak: a felhasználó kéri; utólag személyes adatnak vagy titoknak bizonyul;
  licencprobléma; bizonyítottan hamis. A hamis állításból, ha gyakori tévhit, ellenőrzött `lesson`
  lehet („gyakori hiba: …”).

## 7. Ellentmondások

| Helyzet | Döntés |
|---|---|
| Eltérő `scope` (verzió, platform) | nem ellentmondás: mindkettő igaz, a hatókört pontosítjuk |
| Az egyiket futtatás igazolja, a másikat nem | a futtatott nyer, a másik `contested` |
| Mindkettő tesztelhető | futtatható állítást írunk és lefuttatjuk ([04-tudas-ellenorzese.md](04-tudas-ellenorzese.md)) |
| Egyik sem tesztelhető | a több független, jobb forrás nyer; a másik `contested`, nem törlődik |
| Nem dönthető el | mindkettő `contested`; a válasz kimondja: „a források eltérnek: …” |

## 8. Verzióhoz kötött tudás

- Példák: a `ReactDOM.render` a React 19-ben megszűnt (`createRoot` kell); a Python 3.12-ből
  kikerült a `distutils`. Mindkettő **két elem** külön `scope.range`-dzsel, nem egy felülírt elem.
- Visszakeresés: a verziót az aktuális projektből olvassuk (`package.json`, lock fájlok,
  `pyproject.toml`, `requirements.txt`), és a `range`-re szűrünk. Ha nem ismert, a legújabb stabil
  verzió tudása jön, és a válasz megnevezi, melyik verzióra igaz.
- Új főverzió (a P2 changelog-figyelőből vagy a felhasználó projektjéből): a nyitott tartományú
  elemek (`>=18`) ismétlésre kerülnek az új verzióval; a zárt tartományúak (`<19`) érintetlenek.

## Kész, ha

- minden tudáselemnek van `review` állapota, és az esedékesek bekerülnek a témasorba;
- a `snippet`-ismétlés modell nélkül, csak sandboxban fut, és a bukás `contested`-et eredményez;
- egy szándékosan duplikált tesztkészletből (50 elem, köztük 10 duplikátum, 5 eltérő verziójú
  párral) a deduplikálás a 10-et összevonja, az 5 párt nem;
- ellentmondás soha nem ír felül csendben: minden döntés látszik a `history`-ban;
- a projekt verziója alapján a visszakeresés a megfelelő `scope`-ú elemet adja (teszt React 18/19-re).

## Kapcsolódó

- [02-ejszakai-onallo-tanulas.md](02-ejszakai-onallo-tanulas.md) · [04-tudas-ellenorzese.md](04-tudas-ellenorzese.md) · [01-tanulasi-forrasok.md](01-tanulasi-forrasok.md)
- [../01-architektura/04-tarolas-es-adatfolyam.md](../01-architektura/04-tarolas-es-adatfolyam.md) · [../06-programozas/03-kod-tudasbazis.md](../06-programozas/03-kod-tudasbazis.md)
- [../03-web-szorfozes/03-forrasok-es-bizalom.md](../03-web-szorfozes/03-forrasok-es-bizalom.md) · [../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md](../08-modellek-es-utvonalvalasztas/04-cache-es-ujrahasznositas.md)
