// backgroundLearn.ts — "ALWAYS learn from the web": on every substantive query,
// search the web in the BACKGROUND and ingest the important results into the brain,
// EVEN when the brain already has an answer. Kept cheap and safe so "always" never
// hammers the keyless search or stores junk:
//   • trivial-skip  — greetings / too-few-keyword queries are ignored,
//   • cache         — same topic isn't re-searched (searchCache),
//   • rate-limit    — token bucket caps real searches (rateLimit),
//   • dedupe+rerank — only the best, deduped hits are ingested.
// Fully decoupled via callbacks: the caller passes its own `search` (AI-3's
// /api/search) and `ingest` (AI-1's learnWeb, via brainChat.learnWebHits). Never throws.
import { extractKeywords } from '../lib/memory';
import { redactForSearch } from './redact';
import { dedupeHits } from './dedup';
import { rerankHits } from './rerank';
import { getCachedHits, setCachedHits } from './searchCache';
import { allowRequest } from './rateLimit';
import type { Hit } from './types';

export interface AlwaysLearnDeps<T extends Hit = Hit> {
  /** The caller's web search (e.g. AI-3's searchWeb / POST /api/search). */
  search: (q: string) => Promise<T[]>;
  /** The caller's ingest (e.g. brainChat.learnWebHits → AI-1's learnWeb). */
  ingest: (query: string, hits: T[]) => void;
}

export interface AlwaysLearnOptions {
  /** Skip queries with fewer than this many keywords (greetings, "ok", "thanks"). */
  minKeywords?: number;
  /** Max hits to keep + ingest. */
  top?: number;
  /** Terms to redact from the search query (e.g. the user's name). */
  names?: string[];
}

export type AlwaysLearnReason = 'ok' | 'cached' | 'trivial' | 'rate-limited' | 'no-results' | 'error';

export interface AlwaysLearnResult<T extends Hit = Hit> {
  /** Did we actually hit the network this time? (false for cached/skipped) */
  searched: boolean;
  /** The deduped + reranked hits that were ingested. */
  hits: T[];
  /** The important NEW words found across the hits (not already in the query). */
  terms: string[];
  reason: AlwaysLearnReason;
}

/** Important NEW terms across the hits (titles + snippets) — for storing / a UI chip. */
export function importantTerms<T extends Hit>(query: string, hits: T[], n = 12): string[] {
  const text = hits.map((h) => `${h.title} ${h.snippet}`).join(' ');
  const inQuery = new Set(extractKeywords(query, 8));
  return extractKeywords(text, n * 2)
    .filter((w) => !inQuery.has(w)) // prefer genuinely new knowledge
    .slice(0, n);
}

/**
 * Always learn from the web for a query: search (cached + rate-limited), keep the
 * best deduped/reranked hits, ingest them into the brain, and return the important
 * new terms. Safe to fire-and-forget on every turn — it self-throttles.
 */
export async function alwaysLearn<T extends Hit>(
  query: string,
  deps: AlwaysLearnDeps<T>,
  opts: AlwaysLearnOptions = {},
): Promise<AlwaysLearnResult<T>> {
  const minKeywords = opts.minKeywords ?? 2;
  const top = opts.top ?? 6;
  const empty = (reason: AlwaysLearnReason, searched = false): AlwaysLearnResult<T> => ({
    searched,
    hits: [],
    terms: [],
    reason,
  });

  try {
    const clean = redactForSearch(query, { names: opts.names });
    const kw = extractKeywords(clean, 8);
    if (kw.length < minKeywords) return empty('trivial'); // greetings / chit-chat → don't search

    const primary = kw.join(' ');
    const cached = getCachedHits(primary) as T[] | null;
    let hits: T[];
    let searched = false;

    if (cached) {
      hits = cached; // same topic already fetched recently → reuse, no network
    } else {
      if (!allowRequest()) return empty('rate-limited'); // protect the keyless search
      const raw = await deps.search(primary);
      hits = rerankHits(query, dedupeHits(raw), top);
      setCachedHits(primary, hits);
      searched = true;
    }

    if (!hits.length) return empty('no-results', searched);

    deps.ingest(query, hits); // store region:web docs + grow vocab/Markov (the words)
    return { searched, hits, terms: importantTerms(query, hits, 12), reason: cached ? 'cached' : 'ok' };
  } catch {
    return empty('error');
  }
}
