# Keresés — jó lekérdezés, kulcs nélküli szolgáltató, kímélet, cache

> **Miről szól:** a keresési csővezeték: mikor keresünk, hogyan lesz a kérdésből jó lekérdezés
> (bővítés, kétnyelvűség, hibaüzenet-mód), melyik szolgáltató (kulcs nélküli DuckDuckGo a
> `web/api/search.ts`-ből, opcionálisan helyi SearXNG), és hogyan védjük a forrást és magunkat
> (rate limit, circuit breaker, cache). Mindez a meglévő `web/src/autolearn/**` újrahasznosítása.

## 1. Mikor keresünk — és mikor nem

| Helyzet | Keresés? | Miért |
|---|---|---|
| A tudástár ellenőrzött, friss kártyával lefedi a kérdést | **nem** | gyorsabb, offline (`brainCovers` elve) |
| Lefedi, de a kártya elavult (`isStale`) | igen, frissítésként | TTL lejárt |
| A Kérdező részkérdésének forrása `web` | igen | [../02-belso-parbeszed/03-onkerdezes.md](../02-belso-parbeszed/03-onkerdezes.md) |
| Ismeretlen hibaüzenet / API-név / csomag | igen, hibaüzenet-módban | a doku/Q&A gyakran szó szerint tartalmazza |
| Változékony téma (verzió, kiadás, ár, hír) | igen | `ttlDaysForQuery` → 3 nap |
| Csevegés, köszönés, < 2 kulcsszó | **nem** | `alwaysLearn` „trivial” szabálya |
| A kérdés személyes adatot tartalmaz (`isPersonal`) | **nem**, vagy csak redaktált formában | adatvédelem |
| A felhasználó kikapcsolta a webet (`auri.brain.webSearch` ≠ `1`) | **nem** | opt-in, alapból KI |

## 2. A csővezeték

```
kérdés ─▶ redact (redactForSearch: e-mail, telefon, hosszú szám, a felhasználó neve)
       ─▶ lekérdezés-építés (expandQuery · expandDev · bilingualQueries · hibaüzenet-mód)
       ─▶ cache? (searchCache) ── találat ──────────────────────────────▶ eredmény
       ─▶ rate limit (allowRequest) ── üres vödör ──▶ cache-ből vagy web nélkül
       ─▶ circuit breaker (withBreaker) ── nyitva ──▶ következő szolgáltató / web nélkül
       ─▶ szolgáltató: DuckDuckGo-HTML │ SearXNG (helyi)
       ─▶ összefésülés (mergeSearches: dedupeHits + rerank) ─▶ rerankDev / rerankSmart
       ─▶ eredmény provenance-szel ─▶ oldalolvasás (02) vagy válasz
```

## 3. Lekérdezés-építés

| Szabály | Meglévő kód | Példa |
|---|---|---|
| Kulcsszó-mag, töltelékszavak nélkül | `expandQuery` (`extractKeywords`) | „hogyan tudom rendezni a listát pythonban” → `rendezni listát pythonban` |
| Programozási kérdésnél doku/példa/Q&A változatok | `isProgrammingQuery`, `expandDev` | `… code example`, `… documentation`, `… stackoverflow` |
| Magyar kérdéshez angol változat | `bilingualQueries`, `toEnglishish` | `függvény hiba` → `function error` |
| **Hibaüzenet-mód** (új) | — | a hibaüzenet magja idézőjelben, útvonal/felhasználónév/sorszám nélkül: `"Cannot read properties of undefined" "reading 'map'" react` |
| **Hivatalos doku szűrés** (új) | `findSource` (`seed/sources.ts`) | ismert könyvtárnál `site:docs.python.org …` változat |
| **Verzió** (új) | a projekt függőséglistája | `fastapi 0.11x UploadFile` — csak csomagnév + verzió megy ki, más nem |

Változatszám: interaktívan ≤ 3 (a `mergeSearches` alapértéke), éjjel ≤ 6. A hibaüzenet-mód a lekérdezést
mindig átengedi a `redactForSearch`-en, mert a stack trace gyakran tartalmaz felhasználónevet
(`C:\Users\…`) — ezt az útvonal-szűrő vágja le.

## 4. Szolgáltatók

```ts
interface SearchProvider {
  id: 'ddg' | 'searxng';
  search(q: string, opts: { max: number; lang?: 'hu' | 'en' }): Promise<Hit[]>; // Hit = autolearn/types.ts
}
```

| Szolgáltató | Mi ez | Előny | Hátrány |
|---|---|---|---|
| **DuckDuckGo-HTML** (alap) | a `web/api/search.ts` `ddgSearch`-e: POST `html.duckduckgo.com/html/`, regex-szel bontott találatok, max. 6, lekérdezés ≤ 256 karakter | kulcs nélküli, már működik | a HTML szerkezete változhat; túl sok kérésre blokkolhat |
| **SearXNG** (opcionális, helyi) | saját meta-kereső Dockerben; `GET /search?q=…&format=json` (a JSON-formátumot a `settings.yml`-ben engedélyezni kell) | több motor, JSON, nincs HTML-bontás | plusz szolgáltatás, RAM (mérni kell); a mögötte lévő motorok is korlátozhatnak |

Fizetős API (Brave, Tavily — a `search.ts` fejkommentje említi) csak kulccsal, csak szerveroldalon, és
csak ha a felhasználó kéri; nem része az alaptervnek. **P1-ben** (Auri Core) a `ddgSearch` a helyi
szolgáltatásba költözik, így a Vercel-függvény nem kell a helyi működéshez; a `_guard.ts` védelmei
(SSRF-szűrés, limitek) vele együtt költöznek.

## 5. Kímélet: rate limit és udvariasság

| Réteg | Ma | Javaslat |
|---|---|---|
| Kliens token-bucket | `rateLimit.ts`: 12 keresés / perc | interaktív módban marad |
| Szerver | `_guard.ts`: hívónkénti perc/napi limit (env: `LIMIT_SEARCH_…`) | az Auri Core-ban ugyanez, helyi tárral |
| Éjszakai tanulás | — | külön vödör: ≤ 1 keresés / 10 s, ≤ 150 / éjszaka (kiinduló érték, hangolandó) |
| Ugyanarra a hosztra | — | oldalletöltésnél hosztonként ≥ 2 s szünet ([02-oldalolvasas.md](02-oldalolvasas.md)) |

## 6. Circuit breaker

Ma (`circuitBreaker.ts`): 3 egymást követő hiba → 60 s szünet, utána egy próbakérés (half-open).
Bővítés az Auri Core-hoz:
- **Szolgáltatónként** külön állapot; ha a DDG nyitva van, a SearXNG próbálkozhat.
- **Exponenciális visszalépés** ismételt nyitásnál: 1 → 2 → 4 → … → max. 30 perc (éjjel fontos).
- **„Puha hiba”:** sikeres HTTP-válasz 0 találattal, egymás után többször, eltérő lekérdezésekre →
  valószínű blokk; hibának számít. (A blokkoló oldal pontos jelét mérni kell.)
- Tartalék sorrend: DDG → SearXNG → cache (lejárt is, „régi” jelöléssel) → web nélkül, a válaszban
  kimondva: „most nem tudtam a neten ellenőrizni”.

## 7. Cache

Ma: `searchCache.ts` — localStorage, 6 óra TTL, max. 80 bejegyzés, a normalizált lekérdezés a kulcs.
Az Auri Core-ban SQLite-tábla:

```sql
CREATE TABLE search_cache (
  query_norm TEXT NOT NULL, provider TEXT NOT NULL,
  hits_json  TEXT NOT NULL, fetched_at INTEGER NOT NULL, ttl_s INTEGER NOT NULL,
  PRIMARY KEY (query_norm, provider)
);
```
TTL: változékony téma 1 óra – 1 nap, stabil téma 7 nap (kiinduló értékek); **negatív cache** (0 találat)
1 óra, hogy ugyanazt a reménytelen kérést ne ismételjük. A cache a keresés *találatlistáját* tárolja;
a tudás (kártyák) külön él, saját TTL-lel ([04-tanulas-a-webbol.md](04-tanulas-a-webbol.md)).

## 8. Átköltözés az Auri Core-ba (P1) — mit kell átírni

- A tiszta függvények (`expandQuery`, `rerankHits`, `rerankSmart`, `rerankDev`, `dedupeHits`,
  `domainTrust`, `keySentences`, `redactForSearch`) átvehetők; függőségük a `web/src/lib/memory.ts`
  `extractKeywords`-je — ezt is át kell venni (vagy portolni, ha a Core Pythonban készül).
- A `localStorage`-ra épülők (`searchCache`, `rateLimit`, `circuitBreaker`, `metrics`) tároló-adaptert
  kapnak (SQLite), a logika változatlan.
- Két `detectLang` van (`autolearn/lang.ts`: csak ékezet; `brain/lang.ts`: funkciószavak is) — egy
  közös kell ([../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md](../04-nyelv-es-mondatalkotas/02-magyar-nyelv.md)).

## 9. Mérés és kész-feltétel

Mérőszámok: cache-találati arány, 0-találatos keresések aránya, breaker-nyitások / nap, átlagos
keresési idő, és hogy a találatok közül hány kerül be ellenőrzött tudásként.

**Kész, ha:** (1) a csővezeték az Auri Core-ban fut, mindkét szolgáltatóval, közös interfészen;
(2) egy 30 programozási kérdésből álló készleten a top-3 találat között ≥ 80%-ban van hivatalos doku
vagy elfogadott Q&A-válasz (célérték, mérni kell); (3) kikapcsolt hálózatnál a rendszer 3 hiba után
nem próbálkozik tovább, és a válasz kimondja, hogy nem volt webes ellenőrzés; (4) a kimenő
lekérdezésekben a teszt-PII („Teszt Elek”, fiktív e-mail) soha nem jelenik meg.

## Kapcsolódó

- [02-oldalolvasas.md](02-oldalolvasas.md) · [03-forrasok-es-bizalom.md](03-forrasok-es-bizalom.md) · [04-tanulas-a-webbol.md](04-tanulas-a-webbol.md)
- [../01-architektura/03-hol-fut-auri-core.md](../01-architektura/03-hol-fut-auri-core.md) — hova költözik a keresés
- [../08-modellek-es-utvonalvalasztas/02-router.md](../08-modellek-es-utvonalvalasztas/02-router.md) — mikor kell web egyáltalán
- [../09-biztonsag-es-adatvedelem/01-alapszabalyok.md](../09-biztonsag-es-adatvedelem/01-alapszabalyok.md)
- Meglévő háttér: `ideas_for_brain/autolearn/INTEGRATION.md`, `web/src/autolearn/README.md`
