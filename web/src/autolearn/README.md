# `src/autolearn/**` — minőség- és biztonsági réteg a web-tanuláshoz

> **Új, különálló sáv (AI-4 / LEARN).** Tisztán **additív** segéd-modulok, amelyek a már meglévő
> web-tanuló hurkot (AI-3 `askPipeline` + `api/search.ts`, AI-1 `ingestWeb`, AI-2 web-vizuál)
> **jobbá** teszik, **nem duplikálják**. Ez a mappa **kizárólag ezé a sávé**; egyetlen másik AI
> fájljához sem nyúl, csak **publikus API-t importál olvasásra** (`../lib/memory` `extractKeywords`).
> Új npm csomag nincs. `tsc --noEmit` zöld. Senkit nem blokkol — az integráció opcionális.

## Mit ad (a `brain-autolearn.md` prompt 8–15. szakaszából)

| Modul | Funkció | Prompt-szakasz |
|-------|---------|----------------|
| `redact.ts` | `redactForSearch(query, {names})` — PII (email/telefon/hosszú számok/név) kiszedése **mielőtt** a query a keresőhöz megy | §14 |
| `queryExpansion.ts` | `expandQuery(query)` — nyers üzenet → tiszta kulcsszó-mag + intent-variánsok (`example`, `how to`) | §9 |
| `dedup.ts` | `dedupeHits(hits)` + `textSimilar(a,b)` — URL- és near-duplicate (Jaccard ≥ 0.82) szűrés | §15 |
| `rerank.ts` | `rerankHits(query, hits)` / `scoreHits` — átrangsorolás **kulcsszó-átfedés × forrás-bizalom** alapján | §9 |
| `trust.ts` | `domainTrust(url)` (hivatalos doksi=1), `ttlDaysForQuery`, `isStale` — bizalom + frissesség | §8 |
| `searchCache.ts` | `getCachedHits` / `setCachedHits` — TTL-cache (6 h), ismételt keresés elkerülése (kvóta) | §13 |
| `metrics.ts` | `recordAnswer(source)` / `getMetrics()` — válasz-forrás (brain/web/model) + **brain-hit-rate** (a „okosodik" görbe) | §16 |
| `rateLimit.ts` | `allowRequest()` / `availableTokens()` — token-bucket, a kereső ne legyen hammerelve | §13 |
| `mergeSearches.ts` | `mergeSearches(query, search)` — több query-variáns keresése + összeolvasztás (jobb recall) | §9 |
| `backgroundLearn.ts` | `alwaysLearn(query, {search, ingest})` — **minden** érdemi kérdésnél háttér-keresés + a fontos szavak/adatok beadása az agyba (trivial-skip + cache + rate-limit) | §10 |
| `devFocus.ts` | `rerankDev` / `isProgrammingQuery` / `devTrust` / `expandDev` — **programozó-orientált** rangsor: dev/hivatalos-doksi/kód források előre | §8/§9 |
| `keyContent.ts` | `extractKeyContent(text, query)` / `keySentences` — a **leginformatívabb** mondatok kinyerése (a lényeg, nem a nyers snippet) | §15 |
| `circuitBreaker.ts` | `searchAllowed()` / `recordSearchOutcome(ok)` / `withBreaker` — **hibatűrés**: blokkolásnál visszalép + öngyógyul | §13 |
| `bilingual.ts` | `bilingualQueries(query)` / `toEnglishish` — HU→EN tech-szótár, magyar kérdésnél **angolul is** keres | §9 |
| `relevance.ts` | `rerankSmart(query, hits)` — **TF-IDF + fuzzy** (trigram) rangsor, átfogalmazott/elgépelt kérdésre is | §9 |
| `index.ts` | `prepareQuery(raw)` és `processHits(query, hits)` — kész 1-hívásos kompozítok | — |

## Hogyan köti be AI-3 (opcionális, 1–2 sor az `askPipeline.ts`-ben)

```ts
import { prepareQuery, processHits, getCachedHits, setCachedHits } from '../autolearn';

export async function searchWeb(query: string): Promise<WebHit[]> {
  const { primary } = prepareQuery(query);        // PII-redakció + kulcsszó-mag
  const cached = getCachedHits(primary);
  if (cached) return cached as WebHit[];           // kvóta-spórolás
  const hits = await rawSearch(primary);           // a meglévő /api/search hívás
  const best = processHits(query, hits, 6);        // dedupe + rerank(overlap×trust)
  setCachedHits(primary, best);
  return best;
}
```

AI-1 (`ingestWeb`) ugyanígy használhatja a `processHits`-et a tárolás előtt, és a `trust`/`isStale`
mezőket a `doc`-node súlyozásához / re-fetch-döntéshez. A `WebHit` **strukturálisan kompatibilis** a
lokális `Hit` típussal — nincs típus-import a brain-bridge-ből, így nincs csatolás.

## Zóna-szabályok ([BRAIN_BUILD.md](../../../ideas_for_brain/brain/BRAIN_BUILD.md))
- Csak ide írok: `web/src/autolearn/**`. Más AI fájljához **nem** nyúlok.
- Nincs új függőség (azt csak AI-3 telepít). Nincs séma-/routing-/persona-módosítás.
- Bejelentve a `BRAIN_BUILD.md` státusz-logban (append-only).

> **Áthelyezett tervdokumentumok (2026-11-21):** `ALWAYS_LEARN.md`, `INGEST_WEB.md`,
> `INTEGRATION.md`, `PROGRAMMING_PERSONA.md`, valamint a `brain-*.md` promptok →
> [`ideas_for_brain/`](../../../ideas_for_brain/README.md).
