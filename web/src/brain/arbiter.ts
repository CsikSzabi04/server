// arbiter.ts — the pure "who should answer?" decision (BRAIN.md appendix I).
// Given a query and what the local brain knows, it returns a route + confidence.
// This is ADVISORY logic only: AI-3 wires it into the chat behind a feature flag
// with a safe fallback, so it can never break the existing chat.
import { extractKeywords } from '../lib/memory';
import type { ArbiterDecision } from './contracts';

export interface ArbiterContext {
  vocabSize: number; // how many words the local learner knows
  keywordHits: number; // query keywords the brain recognizes
  queryKeywords: number; // total keywords in the query
  hasRelevantMemory: boolean; // retrieval found strong matches
  localBrainReady: boolean; // the local learner is mature enough to answer
  localBrainCovers: boolean; // the local brain produced a non-trivial answer
  online: boolean;
  localModelAvailable: boolean; // local Ollama reachable (your PC on)
}

/** Is the local (seeded + learned) brain mature enough to answer on its own? */
export function isLocalBrainReady(vocab: number, associations: number): boolean {
  return vocab >= 150 && associations >= 200; // a seeded brain clears this on load
}

/**
 * Decide the answer route. Honest stance: we don't generate fluent text purely
 * locally yet, so 'retrieval' is only chosen when the BRAIN clearly covers the
 * question; otherwise the local model (if up) or the hosted fallback answers.
 */
export function decideRoute(ctx: ArbiterContext): ArbiterDecision {
  const coverage = ctx.queryKeywords > 0 ? ctx.keywordHits / ctx.queryKeywords : 0;

  if (ctx.hasRelevantMemory && coverage >= 0.6) {
    return {
      route: 'retrieval',
      confidence: Math.min(0.9, 0.4 + coverage * 0.5),
      reason: 'Strong memory coverage — the BRAIN can ground the answer.',
    };
  }
  // The local (seeded + learned) brain answers on its own — offline, no API key.
  if (ctx.localBrainReady && ctx.localBrainCovers && coverage >= 0.34) {
    return {
      route: 'local-brain',
      confidence: Math.min(0.8, 0.35 + coverage * 0.45),
      reason: 'The local brain answers from its own learned knowledge (offline, no key).',
    };
  }
  if (ctx.localModelAvailable) {
    return {
      route: 'local-model',
      confidence: 0.7,
      reason: 'Local model available — answering on-device.',
    };
  }
  return {
    route: 'fallback',
    confidence: ctx.online ? 0.6 : 0.2,
    reason: ctx.online ? 'Using the hosted free fallback (Groq/Gemini).' : 'Offline — limited capability.',
  };
}

/** Build an ArbiterContext from a query + the set of keywords the brain knows. */
export function arbiterContext(
  query: string,
  knownKeywords: Set<string>,
  opts: {
    vocabSize?: number;
    hasRelevantMemory?: boolean;
    localBrainReady?: boolean;
    localBrainCovers?: boolean;
    online?: boolean;
    localModelAvailable?: boolean;
  } = {},
): ArbiterContext {
  const qk = extractKeywords(query, 12);
  let hits = 0;
  for (const k of qk) if (knownKeywords.has(k)) hits++;
  return {
    vocabSize: opts.vocabSize ?? 0,
    keywordHits: hits,
    queryKeywords: qk.length,
    hasRelevantMemory: opts.hasRelevantMemory ?? false,
    localBrainReady: opts.localBrainReady ?? false,
    localBrainCovers: opts.localBrainCovers ?? false,
    online: opts.online ?? (typeof navigator !== 'undefined' ? navigator.onLine : true),
    localModelAvailable: opts.localModelAvailable ?? false,
  };
}
