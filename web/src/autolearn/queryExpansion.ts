// queryExpansion.ts — turn a raw user message into better search queries.
// Pure: a redacted keyword-core (stopwords removed via the shared extractKeywords)
// plus a few intent variants. No model needed; works fully offline.
import { extractKeywords } from '../lib/memory';
import { detectLang } from './lang';
import { redactForSearch, type RedactOptions } from './redact';
import type { Lang } from './types';

export interface ExpandOptions extends RedactOptions {
  /** Max number of search-query variants to return (including the primary). */
  max?: number;
}

export interface ExpandedQuery {
  /** The cleaned keyword-core query to search first. */
  primary: string;
  /** Deduped phrasings to try (includes primary), capped to `max`. */
  variants: string[];
  lang: Lang;
}

export function expandQuery(query: string, opts: ExpandOptions = {}): ExpandedQuery {
  const lang = detectLang(query);
  const clean = redactForSearch(query, opts);
  const kw = extractKeywords(clean, 8);
  const core = kw.length ? kw.join(' ') : clean;

  const variants = new Set<string>();
  variants.add(core);
  if (clean && clean !== core) variants.add(clean); // sometimes the full phrasing recalls better
  variants.add(`${core} example`);
  variants.add(`${core} how to`);

  const max = Math.max(1, opts.max ?? 4);
  return { primary: core, variants: [...variants].slice(0, max), lang };
}
