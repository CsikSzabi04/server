// relevance.ts — sharper ranking WITHOUT an embedding model: TF-IDF weighting over
// the hit set (rarer query terms count more) + fuzzy term matching (trigram overlap)
// so paraphrased / mistyped / inflected queries still match the right source. Pure.
import { extractKeywords } from '../lib/memory';
import { domainTrust } from './trust';
import type { Hit } from './types';

function trigrams(s: string): Set<string> {
  const t = ` ${s.toLowerCase()} `;
  const g = new Set<string>();
  for (let i = 0; i < t.length - 2; i++) g.add(t.slice(i, i + 3));
  return g;
}

/** Trigram (Jaccard) similarity of two words, 0..1 — tolerant of typos/inflections. */
function fuzzy(a: string, b: string): number {
  if (a === b) return 1;
  const A = trigrams(a);
  const B = trigrams(b);
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const g of A) if (B.has(g)) inter++;
  return inter / (A.size + B.size - inter);
}

export function rerankSmart<T extends Hit>(query: string, hits: T[], top = 6): T[] {
  const qTerms = extractKeywords(query, 14);
  const hitTerms = hits.map((h) => new Set(extractKeywords(`${h.title} ${h.snippet}`, 24)));

  // document frequency of each query term across the hits → IDF (rarer = stronger)
  const N = hits.length || 1;
  const df = new Map<string, number>();
  for (const term of qTerms) {
    let c = 0;
    for (const ht of hitTerms) if (ht.has(term)) c++;
    df.set(term, c);
  }
  const idf = (term: string): number => Math.log((N + 1) / ((df.get(term) ?? 0) + 1)) + 1;

  return hits
    .map((hit, i) => {
      const ht = hitTerms[i];
      let score = 0;
      for (const term of qTerms) {
        if (ht.has(term)) {
          score += idf(term) * 3; // exact match, weighted by rarity
        } else {
          let best = 0;
          for (const w of ht) {
            const f = fuzzy(term, w);
            if (f > best) best = f;
          }
          if (best >= 0.5) score += best * idf(term) * 1.5; // fuzzy match (typo/inflection)
        }
      }
      return { hit, score: score + domainTrust(hit.url) * 2 };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, top)
    .map((s) => s.hit);
}
