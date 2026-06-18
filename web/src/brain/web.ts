// web.ts — the WEB-LEARNING brain part (3.b). Closes the self-improvement loop:
//   ask → brainCovers? offline answer : search → ingestWeb (store + learn) → next
//   time brainCovers is true, answered from the brain with a source link.
// Uses the live autolearn helpers (dedupe/rerank/trust/freshness); no new deps.
import { processHits, domainTrust, ttlDaysForQuery, isStale } from '../autolearn';
import type { BrainLearner } from './learn';
import { composeLocalAnswer } from './answer';
import { addWebDoc, topCoveringWebDoc } from './webStore';
import type { WebDoc, WebHit } from './contracts';

/**
 * Learn from web search results: store one WebDoc per ranked source (with a
 * domain-trust weight + freshness TTL) and feed the text into the learner so the
 * vocabulary + associations actually grow. Idempotent (processHits dedupes).
 */
export function ingestWeb(learner: BrainLearner, query: string, hits: WebHit[], pages: string[] = []): WebDoc[] {
  const best = processHits(query, hits, 6);
  const fetchedAt = new Date().toISOString();
  const ttlDays = ttlDaysForQuery(query);
  const stored: WebDoc[] = [];
  for (const h of best) {
    const doc: WebDoc = {
      url: h.url,
      title: h.title,
      snippet: h.snippet,
      query,
      weight: 1 + Math.round(domainTrust(h.url) * 4), // 1..5 by source authority
      fetchedAt,
      ttlDays,
    };
    addWebDoc(doc);
    stored.push(doc);
    learner.observe(`${h.title}. ${h.snippet}`, `web:${h.url}`); // vocab + Markov from the result
  }
  for (const text of pages) learner.observe(text, 'web:page'); // cleaned page text → direct learning
  learner.observe(query, 'web:query'); // reinforce the recurring topic
  return stored;
}

/**
 * "Does the brain already cover this, freshly?" — used by the pipeline to decide
 * brain-first vs. a web search. Returns the local answer when covered AND the
 * covering web fact (if any) is still fresh; otherwise reports not-covered so the
 * caller searches the web and ingestWeb() refreshes it.
 */
export function brainCovers(
  learner: BrainLearner,
  query: string,
  facts: string[] = [],
): { covered: boolean; answer: string } {
  const answer = composeLocalAnswer(learner, query, facts).trim();
  if (!answer) return { covered: false, answer: '' };
  const doc = topCoveringWebDoc(query);
  if (doc && isStale(doc.fetchedAt, doc.ttlDays)) return { covered: false, answer: '' }; // stale → re-fetch
  return { covered: true, answer };
}
