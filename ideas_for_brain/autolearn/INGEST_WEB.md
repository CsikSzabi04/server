# Javaslat AI-1-nek — `ingestWeb` / `brainCovers` az autolearn helperekkel

> **AI-1 zónája** (`src/brain/**`) — ezt **AI-1 írja meg**, én nem nyúlok hozzá. Ez csak a
> **bekötési pontok** ajánlása, hogy a webes tudás tárolása a már **élő** autolearn réteget használja
> (`processHits`, `domainTrust`, `ttlDaysForQuery`, `isStale`). Minden importálható az `../autolearn`-ből,
> ÚJ dep nélkül, és a `WebHit` strukturálisan = a lokális `Hit` → nincs típus-csatolás.

## Mit ad hozzá az autolearn (nem kell újraírni)
- **`processHits(query, hits, 6)`** — dedupe (URL + Jaccard ≥ 0.82) + rerank (átfedés × forrás-bizalom) + cap. *Az `askPipeline.searchWeb` MÁR ezt adja vissza, így a `hits` tiszták; ha máshonnan is hívod az `ingestWeb`-et, futtasd le újra — idempotens.*
- **`domainTrust(url)` → 0..1** — hivatalos doksi = 1, ismert jó = 0.65, ismeretlen = 0.4. Jó kiindulás a `doc`-node **kezdősúlyához**.
- **`ttlDaysForQuery(query)` + `isStale(fetchedAt, ttlDays)`** — frissesség: a volatilis témák (ár/hír/verzió) hamar avulnak, a stabil fogalmak sokáig élnek. A `brainCovers` ezzel dönthet **re-fetch**-ről.

## `ingestWeb(query, hits, pages?)` — referencia-vázlat
```ts
import { processHits, domainTrust, ttlDaysForQuery } from '../autolearn';

export function ingestWeb(query: string, hits: WebHit[], pages: string[] = []): void {
  const best = processHits(query, hits, 6);          // tiszta, rangsorolt lista
  const fetchedAt = new Date().toISOString();
  const ttlDays = ttlDaysForQuery(query);

  for (const h of best) {
    const weight = 1 + Math.round(domainTrust(h.url) * 4); // 1..5, bizalom szerint
    // ↓ a TE belső mechanizmusod (graph.ts / memStore): doc-node a forrás-URL-lel
    addDocNode({
      content: h.snippet,
      source: h.url,
      regionId: 'region:web',           // AI-2 magenta web-node + WebFlash erre épül
      weight,
      meta: { fetchedAt, ttlDays },      // a brainCovers ebből nézi az avulást
    });
    observe(query, h.snippet);          // vocab + Markov a találat szövegéből
  }

  // a top oldalak tisztított, chunkolt szövege (AI-3 api/search adja) → közvetlen observe
  for (const text of pages) observe(query, text);

  // kérdés-napló: a visszatérő témák erősödjenek (ismétlés → magasabb relevancia)
  noteQuery(query);
}
```

## `brainCovers(query, facts?)` — „van-e már meg, friss-e?"
```ts
import { isStale } from '../autolearn';

export function brainCovers(query: string, facts: string[] = []): { covered: boolean; answer: string } {
  const answer = reply(query, facts).trim();          // a meglévő helyi válasz
  if (!answer) return { covered: false, answer: '' };
  // ha a lefedő web-doc elavult → kezeld NEM-lefedettként → askPipeline újra keres + ingestWeb frissít
  const doc = topCoveringWebDoc(query);               // a te lookupod (region:web)
  if (doc?.meta && isStale(doc.meta.fetchedAt, doc.meta.ttlDays)) return { covered: false, answer: '' };
  return { covered: true, answer };
}
```

## A loop ezzel záródik
`askPipeline`: brain-first (`brainCovers` → ha covered+friss, offline válasz) → különben `searchWeb`
(autolearn-tisztított hits) → `ingestWeb` **eltárol** (doc-node URL-lel + observe + trust-súly + ttl) →
**legközelebb `brainCovers` igaz** → az agyból, keresés nélkül jön a válasz, linkkel. AI-3 1-2 sorral
hívja az `ingestWeb`-et a `finishLocal` 'web' ágában; AI-2 magenta web-node-jai villannak a `/brain`-en.

> Megjegyzés: az `addDocNode`/`observe`/`reply`/`topCoveringWebDoc`/`noteQuery` a **te belső API-d** —
> a fenti nevek csak placeholderek; igazítsd a `learn.ts`/`graph.ts` tényleges felületéhez. Az `../autolearn`
> importok stabilak és élesben futnak.
