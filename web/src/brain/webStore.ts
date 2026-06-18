// webStore.ts — the brain's WEB-LEARNED facts (3.b). When the brain can't answer
// from what it knows, the pipeline searches the web and ingestWeb() stores the
// results here: one WebDoc per source URL (with domain-trust weight + freshness
// TTL). These render as the magenta `region:web` nodes on /brain, and brainCovers()
// uses their freshness to decide when to re-fetch. Persisted in IndexedDB (no 5 MB
// cap), keyed by URL so re-learning a source updates it in place.
import { idbGet, idbSet } from '../brain-bridge/idb';
import { extractKeywords } from '../lib/memory';
import type { WebDoc } from './contracts';

const KEY = 'auri.brainWeb';
const MAX_WEB_DOCS = 4_000;

const docs = new Map<string, WebDoc>(); // url → doc
const keysOf = new Map<string, Set<string>>(); // url → query/snippet keywords (for coverage)
let loaded = false;

function indexDoc(d: WebDoc): void {
  const kws = new Set([...extractKeywords(d.query, 8), ...extractKeywords(`${d.title} ${d.snippet}`, 12)]);
  keysOf.set(d.url, kws);
}

/** Load persisted web docs once (call on init). */
export async function loadWebDocs(): Promise<void> {
  if (loaded) return;
  loaded = true;
  try {
    const saved = await idbGet<WebDoc[]>(KEY);
    if (Array.isArray(saved)) for (const d of saved) {
      docs.set(d.url, d);
      indexDoc(d);
    }
  } catch {
    /* ignore */
  }
}

function persist(): void {
  void idbSet(KEY, [...docs.values()].slice(-MAX_WEB_DOCS));
}

/** Add or update a web doc (keyed by URL). Returns true if it was new. */
export function addWebDoc(d: WebDoc): boolean {
  const isNew = !docs.has(d.url);
  docs.set(d.url, d);
  indexDoc(d);
  if (docs.size > MAX_WEB_DOCS) {
    // drop the oldest by fetchedAt
    const oldest = [...docs.values()].sort((a, b) => (a.fetchedAt < b.fetchedAt ? -1 : 1))[0];
    if (oldest) {
      docs.delete(oldest.url);
      keysOf.delete(oldest.url);
    }
  }
  persist();
  return isNew;
}

export function getWebDocs(): WebDoc[] {
  return [...docs.values()];
}
export function webDocCount(): number {
  return docs.size;
}

/** The stored web doc whose keywords best overlap the query (or null). */
export function topCoveringWebDoc(query: string): WebDoc | null {
  const qk = new Set(extractKeywords(query, 12));
  if (qk.size === 0) return null;
  let best: WebDoc | null = null;
  let bestScore = 0;
  for (const [url, kws] of keysOf) {
    let hits = 0;
    for (const k of qk) if (kws.has(k)) hits++;
    if (hits > bestScore) {
      bestScore = hits;
      best = docs.get(url) ?? null;
    }
  }
  return bestScore >= 2 ? best : null;
}
