// askPipeline — AI-3 (BODY) web-learning glue (BRAIN_BUILD §5.b).
// Flow: BRAIN first (offline, key-free) → if the brain has nothing AND web search
// is enabled, search the web (keyless DuckDuckGo via /api/search) and answer from
// the results with links → otherwise null, so the chat falls back to the model.
//
// Self-improvement (storing web results back into the brain so it "covers" the
// topic next time) lands when AI-1 ships ingestWeb(); this module already returns
// the hits so the caller can feed them in.

import { prepareQuery, processHits, getCachedHits, setCachedHits, allowRequest } from '../autolearn';

export interface WebHit {
  title: string;
  url: string;
  snippet: string;
}

export interface AskResult {
  answer: string;
  source: 'brain' | 'web';
  hits: WebHit[];
}

const FLAG = 'auri.brain.webSearch'; // opt-in: '1' enables the web fallback (default OFF)
const SEARCH_URL = '/api/search'; // same-origin serverless function (dev proxy in dev)

/** Is the web-search fallback opted in? (default OFF — it makes external requests) */
export function webSearchEnabled(): boolean {
  try {
    return localStorage.getItem(FLAG) === '1';
  } catch {
    return false;
  }
}

export function setWebSearchEnabled(on: boolean): void {
  try {
    localStorage.setItem(FLAG, on ? '1' : '0');
  } catch {
    /* storage blocked */
  }
}

/** Raw keyless web search via the serverless function. Never throws (returns []). */
async function rawSearch(query: string): Promise<WebHit[]> {
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

/**
 * Web search with the autolearn quality layer (AI-4): redact PII + distil the
 * query to a keyword core, reuse a TTL-cached result (saves quota + latency),
 * then dedupe + rerank hits by keyword-overlap × source-trust.
 */
export async function searchWeb(query: string): Promise<WebHit[]> {
  const { primary } = prepareQuery(query);
  const cached = getCachedHits(primary);
  if (cached) return cached as WebHit[];
  if (!allowRequest()) return []; // rate-limit (AI-4 token-bucket) → don't hammer DDG
  const best = processHits(query, await rawSearch(primary), 6);
  setCachedHits(primary, best);
  return best;
}

/** Like rawSearch but also asks the server for the top pages' text (deep learning). */
async function rawSearchDeep(query: string, pages: number): Promise<{ hits: WebHit[]; pages: string[] }> {
  try {
    const res = await fetch(SEARCH_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query, pages }),
      signal: AbortSignal.timeout(16_000),
    });
    if (!res.ok) return { hits: [], pages: [] };
    const j = (await res.json()) as { results?: WebHit[]; pages?: string[] };
    return {
      hits: Array.isArray(j.results) ? j.results : [],
      pages: Array.isArray(j.pages) ? j.pages : [],
    };
  } catch {
    return { hits: [], pages: [] };
  }
}

/**
 * Deep web search for the explicit web-answer branch: fetches the top result pages'
 * text too, so the brain can learn the ESSENCE (distilled by AI-4's extractKeyContent),
 * not just snippets. Fresh each call — the hits cache only holds snippets — but still
 * rate-limited (falls back to cached snippets when the bucket is empty).
 */
export async function searchWebDeep(query: string): Promise<{ hits: WebHit[]; pages: string[] }> {
  const { primary } = prepareQuery(query);
  if (!allowRequest()) {
    const cached = getCachedHits(primary);
    return { hits: (cached as WebHit[]) ?? [], pages: [] };
  }
  const { hits, pages } = await rawSearchDeep(primary, 2);
  const best = processHits(query, hits, 6);
  setCachedHits(primary, best);
  return { hits: best, pages };
}

/** Build a readable answer from web hits, with the source links inline. */
export function composeWebAnswer(query: string, hits: WebHit[]): string {
  const top = hits.slice(0, 4);
  const body = top
    .map((h, i) => `${i + 1}. ${h.title}${h.snippet ? `\n   ${h.snippet}` : ''}\n   ${h.url}`)
    .join('\n\n');
  return `🌐 I looked this up on the web for "${query}":\n\n${body}`;
}

/**
 * BRAIN-first ask pipeline. Pass the brain's own answer (from brainChat.localAnswer);
 * if it's empty and web search is enabled, returns a web answer + hits; otherwise
 * null → the caller runs the model.
 */
export async function askPipeline(query: string, brainAnswer: string | null): Promise<AskResult | null> {
  if (brainAnswer) return { answer: brainAnswer, source: 'brain', hits: [] };
  if (!webSearchEnabled()) return null;
  const hits = await searchWeb(query);
  if (!hits.length) return null;
  return { answer: composeWebAnswer(query, hits), source: 'web', hits };
}
