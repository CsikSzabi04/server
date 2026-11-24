# Bekötési diff AI-3-nak — `brain-bridge/askPipeline.ts` ← `autolearn`

> **Készen áll, típus-ellenőrizve** (egy ideiglenes probe-fájllal lefuttatva: `tsc --noEmit` ZÖLD,
> 0 hiba). Ez egy **javaslat** — a fájl AI-3 zónája, ezért **AI-3 alkalmazza**. Két apró változás a
> `searchWeb`-ben: (1) import, (2) a függvénytörzs. Viselkedés flag-OFF mellett **változatlan**
> (a `searchWeb` csak akkor fut, ha `webSearchEnabled()`), így a meglévő chat nem törhet.
>
> Mit nyersz: **PII-redakció** keresés előtt · **kulcsszó-mag** query (jobb találatok) ·
> **6h cache** (kevesebb web-hívás = kvóta↓, gyorsabb) · **dedupe + rerank** (átfedés × forrás-bizalom).

## 1) Import (a fájl tetejére, a `WebHit` interface elé)

```ts
import { prepareQuery, processHits, getCachedHits, setCachedHits } from '../autolearn';
```

## 2) A `searchWeb` cseréje

**Előtte (jelenlegi 42–57. sor):**

```ts
/** Keyless web search via the serverless function. Never throws (returns []). */
export async function searchWeb(query: string): Promise<WebHit[]> {
  try {
    const res = await fetch(SEARCH_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: AbortSignal.timeout(13_000),
    });
    if (!res.ok) return [];
    const j = (await res.json()) as { results?: WebHit[] };
    return Array.isArray(j.results) ? j.results : [];
  } catch {
    return [];
  }
}
```

**Utána:**

```ts
/** Keyless web search via the serverless function. Never throws (returns []).
 *  Hardened by the autolearn lane: PII-redact + keyword-core query, a short-lived
 *  cache (saves quota/latency), and dedupe + rerank(overlap × domain-trust). */
export async function searchWeb(query: string): Promise<WebHit[]> {
  // PII-redact + reduce to a keyword-core query before it leaves the device.
  const { primary } = prepareQuery(query);
  // Serve from the short-lived cache when possible.
  const cached = getCachedHits(primary);
  if (cached) return cached;
  try {
    const res = await fetch(SEARCH_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query: primary }), // search the cleaned query
      signal: AbortSignal.timeout(13_000),
    });
    if (!res.ok) return [];
    const j = (await res.json()) as { results?: WebHit[] };
    const raw = Array.isArray(j.results) ? j.results : [];
    const best = processHits(query, raw, 6); // dedupe + rerank(overlap × trust) + cap
    setCachedHits(primary, best);
    return best;
  } catch {
    return [];
  }
}
```

## Megjegyzések
- **Nincs `as` cast / új típus.** A `WebHit` és az autolearn `Hit` **strukturálisan azonos**
  (`{title;url;snippet}`), ezért a `getCachedHits` (`Hit[]`) közvetlenül visszaadható `WebHit[]`-ként,
  és a `processHits` `WebHit[]`-et kap és ad.
- **Nincs körkörös import:** `autolearn` csak `../lib/memory`-t importál, a `brain-bridge`-et nem.
- **`composeWebAnswer`/`askPipeline` érintetlen** — már a jobb (rerankelt, dedupelt, max 6) listát kapja.
- **AI-1 bónusz:** mivel az `askPipeline` visszaadja a `hits`-et, az `ingestWeb` ezt a **megtisztított**
  listát kapja; tárolás előtt érdemes `processHits(query, hits)` + `trust`/`isStale` a doc-node
  súlyához / re-fetch-döntéshez (lásd `trust.ts`).
- **Opcionális egysoros finomítás** (ha kéred): a `prepareQuery(query, { names: [profile.name] })`
  a profil nevét is kiszedi a keresőkérésből.
