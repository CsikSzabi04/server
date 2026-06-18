// autolearn — pure, additive helpers that improve the web-learning loop WITHOUT
// touching the AIs' zones (src/brain = AI-1, brain-bridge = AI-3, brain-view = AI-2).
// Everything here is dependency-free and read-only over shared code; AI-3's
// askPipeline can opt in with 1–2 lines (see README.md). Owned by the autolearn lane.
//
//   prepareQuery(raw, { names })   → redact PII + expand into better search queries
//   processHits(query, hits)       → dedupe + rerank by overlap×trust + cap
//   getCachedHits / setCachedHits  → skip repeat searches (quota + latency)
//   domainTrust / ttlDaysForQuery / isStale → trust + freshness scoring
export * from './types';
export { detectLang } from './lang';
export { redactForSearch, type RedactOptions } from './redact';
export { expandQuery, type ExpandedQuery, type ExpandOptions } from './queryExpansion';
export { domainTrust, ttlDaysForQuery, isStale } from './trust';
export { textSimilar, dedupeHits } from './dedup';
export { scoreHits, rerankHits } from './rerank';
export { getCachedHits, setCachedHits, clearSearchCache } from './searchCache';
export { recordAnswer, getMetrics, resetMetrics, type AnswerSource, type BrainMetrics } from './metrics';
export { allowRequest, availableTokens, type RateLimitOptions } from './rateLimit';
export { mergeSearches, type MergeOptions } from './mergeSearches';
export {
  alwaysLearn,
  importantTerms,
  type AlwaysLearnDeps,
  type AlwaysLearnOptions,
  type AlwaysLearnResult,
  type AlwaysLearnReason,
} from './backgroundLearn';
export { isProgrammingQuery, devTrust, rerankDev, expandDev } from './devFocus';
export { keySentences, extractKeyContent, type KeyContentOptions } from './keyContent';
export { searchAllowed, recordSearchOutcome, withBreaker } from './circuitBreaker';
export { toEnglishish, bilingualQueries } from './bilingual';
export { rerankSmart } from './relevance';

import { expandQuery, type ExpandOptions, type ExpandedQuery } from './queryExpansion';
import { dedupeHits } from './dedup';
import { rerankHits } from './rerank';
import type { Hit } from './types';

/** One call: clean (PII-redact) + expand a raw user message into search queries. */
export function prepareQuery(raw: string, opts: ExpandOptions = {}): ExpandedQuery {
  return expandQuery(raw, opts);
}

/** One call on api/search results: dedupe → rerank(overlap×trust) → cap to `top`. */
export function processHits<T extends Hit>(query: string, hits: T[], top = 6): T[] {
  return rerankHits(query, dedupeHits(hits), top);
}
