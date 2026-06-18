// rerank.ts — re-score web hits against the query (keyword overlap × domain trust)
// before they are stored/cited, so the best, most authoritative sources win. Uses
// the shared extractKeywords (read-only import), same signal as relevantMemories.
import { extractKeywords } from '../lib/memory';
import { domainTrust } from './trust';
import type { Hit, ScoredHit } from './types';

export function scoreHits<T extends Hit>(query: string, hits: T[]): ScoredHit<T>[] {
  const qk = new Set(extractKeywords(query, 12));
  return hits
    .map((hit) => {
      let overlap = 0;
      for (const k of extractKeywords(`${hit.title} ${hit.snippet}`, 16)) if (qk.has(k)) overlap++;
      const trust = domainTrust(hit.url);
      return { hit, score: overlap * 5 + trust * 4, trust, overlap };
    })
    .sort((a, b) => b.score - a.score);
}

/** Best hits first, capped to `top`. Convenience over scoreHits. */
export function rerankHits<T extends Hit>(query: string, hits: T[], top = 6): T[] {
  return scoreHits(query, hits)
    .slice(0, top)
    .map((s) => s.hit);
}
