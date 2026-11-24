// webStore.ts — the brain's WEB-LEARNED facts (3.b). When the brain can't answer
// from what it knows, the pipeline searches the web and ingestWeb() stores the
// results here: one WebDoc per source URL (with domain-trust weight + freshness
// TTL). These render as the magenta `region:web` nodes on /brain, and brainCovers()
// uses their freshness to decide when to re-fetch. Persisted in IndexedDB (no 5 MB
// cap), keyed by URL so re-learning a source updates it in place.
//
// PRIVACY (SECURITY.md §4.4): each doc carries the query that fetched it, so the
// store is kept PER IDENTITY ('auri.brainWeb.guest' / 'auri.brainWeb.u.<userId>').
// Switching identity swaps the in-memory set at once. The old shared key
// ('auri.brainWeb') is handed once to the first account that signs in here and is
// never shown to a guest.
import { idbGet, idbSet, idbDel } from '../brain-bridge/idb';
import { extractKeywords } from '../lib/memory';
import { scopedKey } from '../lib/storageScope';
import type { WebDoc } from './contracts';

const BASE = 'auri.brainWeb';
const CLAIMED_FLAG = `${BASE}.claimed`;
const MAX_WEB_DOCS = 4_000;
const keyFor = (userId: string | null): string => (userId ? scopedKey(BASE, userId) : `${BASE}.guest`);

const docs = new Map<string, WebDoc>(); // url → doc
const keysOf = new Map<string, Set<string>>(); // url → query/snippet keywords (for coverage)
let loadedFor: string | null | undefined = undefined; // identity whose docs are in memory
let currentKey = keyFor(null);
let loadGen = 0;

function indexDoc(d: WebDoc): void {
  const kws = new Set([...extractKeywords(d.query, 8), ...extractKeywords(`${d.title} ${d.snippet}`, 12)]);
  keysOf.set(d.url, kws);
}

async function claimLegacy(userId: string): Promise<void> {
  try {
    if (localStorage.getItem(CLAIMED_FLAG)) return;
  } catch {
    return;
  }
  const legacy = await idbGet<WebDoc[]>(BASE);
  if (Array.isArray(legacy) && !Array.isArray(await idbGet(keyFor(userId)))) await idbSet(keyFor(userId), legacy);
  await idbDel(BASE);
  try {
    localStorage.setItem(CLAIMED_FLAG, '1');
  } catch {
    /* storage blocked */
  }
}

/** Load this identity's persisted web docs (guest = null). Swapping identity clears
 *  the previous identity's docs from memory immediately, before anything is awaited. */
let loading: Promise<void> | null = null;

export async function loadWebDocs(userId: string | null = null): Promise<void> {
  if (loadedFor === userId) return loading ?? undefined;
  const gen = ++loadGen;
  docs.clear();
  keysOf.clear();
  loadedFor = userId;
  currentKey = keyFor(userId);
  const run = (async () => {
    try {
      if (userId) await claimLegacy(userId);
      const saved = await idbGet<WebDoc[]>(keyFor(userId));
      if (gen !== loadGen) return; // identity changed while loading → the newer load wins
      if (Array.isArray(saved))
        for (const d of saved) {
          if (!docs.has(d.url)) docs.set(d.url, d); // a doc added during the load is newer
          indexDoc(docs.get(d.url)!);
        }
    } catch {
      /* ignore */
    }
  })();
  loading = run;
  await run;
  if (loading === run) loading = null;
}

function persist(): void {
  const key = currentKey;
  // While the stored set is still loading, writing now would REPLACE it with a partial
  // set (data loss) — wait for the load, then write the merged set.
  if (loading) {
    void loading.then(() => {
      if (key === currentKey) void idbSet(key, [...docs.values()].slice(-MAX_WEB_DOCS));
    });
    return;
  }
  void idbSet(key, [...docs.values()].slice(-MAX_WEB_DOCS));
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
