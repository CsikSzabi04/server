// searchCache.ts — tiny TTL cache for web results, so repeated questions don't
// re-hit the search provider (saves quota + latency). localStorage-backed, capped,
// and never throws (storage may be blocked/full). Pure of the AIs' modules.
import type { Hit } from './types';

const KEY = 'auri.autolearn.searchCache';
const TTL_MS = 6 * 60 * 60 * 1000; // 6 hours
const MAX_ENTRIES = 80;

interface Entry {
  hits: Hit[];
  at: number;
}
type Store = Record<string, Entry>;

function norm(query: string): string {
  return query.toLowerCase().replace(/\s+/g, ' ').trim();
}

function read(): Store {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') as Store;
  } catch {
    return {};
  }
}

function write(s: Store): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* storage blocked or full — caching is best-effort */
  }
}

export function getCachedHits(query: string): Hit[] | null {
  const e = read()[norm(query)];
  if (!e || Date.now() - e.at > TTL_MS) return null;
  return e.hits;
}

export function setCachedHits(query: string, hits: Hit[]): void {
  const s = read();
  s[norm(query)] = { hits, at: Date.now() };
  const entries = Object.entries(s);
  if (entries.length > MAX_ENTRIES) {
    entries.sort((a, b) => a[1].at - b[1].at); // oldest first
    for (const [k] of entries.slice(0, entries.length - MAX_ENTRIES)) delete s[k];
  }
  write(s);
}

export function clearSearchCache(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
}
