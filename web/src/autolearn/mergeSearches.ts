// mergeSearches.ts — run several query variants through a caller-provided search
// function and merge the results (dedupe + rerank by overlap × trust). Improves
// recall on hard/rare questions WITHOUT coupling to the search transport: the
// caller passes its own `search` (e.g. AI-3's /api/search call). Never throws.
import { expandQuery, type ExpandOptions } from './queryExpansion';
import { dedupeHits } from './dedup';
import { rerankHits } from './rerank';
import type { Hit } from './types';

export interface MergeOptions extends ExpandOptions {
  /** How many query variants to search (incl. the primary). Default 3. */
  variants?: number;
  /** Final cap on merged hits. Default 6. */
  top?: number;
}

export async function mergeSearches<T extends Hit>(
  query: string,
  search: (q: string) => Promise<T[]>,
  opts: MergeOptions = {},
): Promise<T[]> {
  const { variants } = expandQuery(query, opts);
  const queries = variants.slice(0, Math.max(1, opts.variants ?? 3));
  const results = await Promise.all(queries.map((q) => search(q).catch(() => [] as T[])));
  const all: T[] = [];
  for (const r of results) all.push(...r);
  return rerankHits(query, dedupeHits(all), opts.top ?? 6);
}
