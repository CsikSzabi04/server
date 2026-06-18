// dedup.ts — drop duplicate web hits by normalized URL and near-duplicate snippet
// (Jaccard ≥ threshold), mirroring BRAIN.md's textSimilar dedup so the same fact
// doesn't pile up in memory. Pure, generic over any Hit-shaped object.
import type { Hit } from './types';

function normUrl(url: string): string {
  try {
    const u = new URL(url);
    return (u.hostname.replace(/^www\./, '') + u.pathname.replace(/\/+$/, '')).toLowerCase();
  } catch {
    return url.trim().toLowerCase();
  }
}

function tokens(s: string): Set<string> {
  return new Set(s.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) ?? []);
}

/** Jaccard similarity of two short texts (0..1). */
export function textSimilar(a: string, b: string): number {
  const A = tokens(a);
  const B = tokens(b);
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const t of A) if (B.has(t)) inter++;
  return inter / (A.size + B.size - inter);
}

export function dedupeHits<T extends Hit>(hits: T[], simThreshold = 0.82): T[] {
  const out: T[] = [];
  const seen = new Set<string>();
  for (const h of hits) {
    const key = normUrl(h.url);
    if (seen.has(key)) continue;
    if (out.some((o) => textSimilar(o.snippet || o.title, h.snippet || h.title) >= simThreshold)) continue;
    seen.add(key);
    out.push(h);
  }
  return out;
}
