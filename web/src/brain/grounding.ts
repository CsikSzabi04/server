// grounding.ts — H1 of the hybrid (brain + Ollama): BRAIN → MODEL grounding.
// Before a model call, the brain assembles a compact, token-budgeted block of the
// knowledge it has that is RELEVANT to the query (curated facts, a code example +
// source, web-learned facts, the associated concepts it knows, personal facts, and
// any recalled Q→A). Injected into the model's system message so a small local model
// (e.g. gemma2:2b) answers GROUNDED in our brain's knowledge — and cites the sources.
import { extractKeywords, type Memory } from '../lib/memory';
import type { BrainLearner } from './learn';
import { detectLang } from './lang';
import { findKnowledge } from './seed/knowledge';
import { findSnippet } from './seed/programmingCurated';
import { topCoveringWebDoc } from './webStore';
import { pickFacts } from './answer';

const CHAR_BUDGET = 1400; // keep the block small so it never blows up the prompt

// Function words to drop from "related concepts" (Markov neighbours are noisy).
const STOP = new Set<string>(
  (
    'the and is are was were a an of to in on at by for with as it its this that these those or ' +
    'be been being have has had do does did not no yes you your they them their we our he she his her ' +
    'egy az és van nem igen vagy mi te ő ők ti hogy ezek azok ami amit aki ott itt is már csak még ' +
    'offline brain'
  ).split(/\s+/),
);

/**
 * Build the "BRAIN KNOWLEDGE" grounding block for a query (empty string if the brain
 * has nothing relevant — then the model answers normally). Pure: no I/O, no network.
 */
export function buildBrainContext(learner: BrainLearner, query: string, memories: Memory[] = []): string {
  const lang = detectLang(query);
  const parts: string[] = [];

  // 1) curated general/tech knowledge — a clean, factual sentence
  const known = findKnowledge(query, lang);
  if (known) parts.push(`• Fact: ${known}`);

  // 2) a verbatim code example + official source (programming queries)
  const snippet = findSnippet(query);
  if (snippet) parts.push(`• Code (${snippet.title}):\n${snippet.code}\n  Source: ${snippet.source}`);

  // 3) something the brain learned from the web earlier, with its source link
  const web = topCoveringWebDoc(query);
  if (web?.snippet) parts.push(`• From the web: ${web.snippet} (Source: ${web.url})`);

  // 4) ASSOCIATIONS — what the brain knows is connected to the query terms.
  // Filter out function words (Markov neighbours are often "is/the/and/az/egy") so
  // only meaningful concepts remain.
  const related = new Set<string>();
  for (const w of extractKeywords(query, 6)) {
    for (const n of learner.neighbors(w, 10)) {
      const word = n.word;
      if (word.length >= 3 && !STOP.has(word)) related.add(word);
    }
  }
  if (related.size) parts.push(`• Related concepts: ${[...related].slice(0, 12).join(', ')}`);

  // 5) personal facts from memory (read-only)
  const facts = pickFacts(memories, query, 3);
  if (facts.length) parts.push(`• About the user: ${facts.join(' | ')}`);

  // 6) a previously learned Q→A (if it adds something the fact didn't)
  const recalled = learner.recall(query)?.trim();
  if (recalled && recalled !== known) parts.push(`• Learned earlier: ${recalled}`);

  if (!parts.length) return '';
  let block = parts.join('\n');
  if (block.length > CHAR_BUDGET) block = `${block.slice(0, CHAR_BUDGET)}…`;

  const lead =
    lang === 'hu'
      ? 'AURI AGY-TUDÁS (valódi, megalapozott tudás erről a kérdésről — kezeld igazságként, építs rá, és idézd a forrásokat; ha hiányos, mondd ki, ne találj ki):'
      : 'AURI BRAIN KNOWLEDGE (real, grounded knowledge for this question — treat it as ground truth, build on it, and cite the sources; if it is incomplete, say so, do not invent):';
  return `${lead}\n${block}`;
}
