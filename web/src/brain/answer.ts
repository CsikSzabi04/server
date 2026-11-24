// answer.ts — composes the LOCAL-BRAIN reply with a clear PRIORITY of sources, so
// the brain returns CLEAN, whole sentences in the user's language (offline, no key):
//   1) a build-a-website/app template (code),
//   2) a curated programming snippet + official source,
//   3) a curated general-knowledge answer in the detected language,
//   4) a learned Q→A recall (clean, because seeded/learned answers are whole),
//   5) a personal fact wrapped in a natural sentence frame,
//   6) Markov phrasing only as a LAST resort (it babbles on a small corpus).
// Reads the personal layer (Memory[]) read-only.
import { extractKeywords, type Memory } from '../lib/memory';
import type { BrainLearner } from './learn';
import { detectLang } from './lang';
import { isPersonal } from './privacy';
import { findSnippet } from './seed/programmingCurated';
import { findSource } from './seed/sources';
import { findRecipe, renderRecipe } from './seed/recipes';
import { findKnowledge } from './seed/knowledge';
import { topCoveringWebDoc } from './webStore';
import { coversQuery } from './relevance';

/** Top personal facts / doc snippets relevant to the query (read-only over memory). */
export function pickFacts(memories: Memory[], query: string, n = 3): string[] {
  const qk = new Set(extractKeywords(query, 12));
  return memories
    .filter((m) => m.kind === 'fact' || m.kind === 'summary' || m.kind === 'doc')
    .map((m) => {
      let overlap = 0;
      for (const k of extractKeywords(m.content, 10)) if (qk.has(k)) overlap++;
      // Pinned / heavy memories RANK higher, but only a real keyword overlap makes a
      // memory RELEVANT — otherwise a pinned profile fact answered every message
      // ("nem", "nmem", …) with the user's whole profile.
      const score = (m.pinned ? 100 : 0) + (m.weight ?? 1) + overlap * 5;
      return { m, score, overlap };
    })
    .filter((x) => x.overlap > 0 && x.score >= 6)
    .sort((a, b) => b.score - a.score)
    .slice(0, n)
    .map((x) => x.m.content);
}

/** Wrap a retrieved fact in a short, natural sentence frame in the user's language. */
function frameFact(fact: string, lang: 'hu' | 'en' | 'de' | 'unknown'): string {
  const f = fact.trim().replace(/\s+/g, ' ');
  if (lang === 'hu') return `Amit erről tudok: ${f}`;
  if (lang === 'de') return `Was ich darüber weiß: ${f}`;
  return `Here is what I know: ${f}`;
}

/**
 * Build the local-brain answer following the priority above. Returns '' only when
 * nothing useful can be said — the caller then falls back to the next route.
 */
export function composeLocalAnswer(learner: BrainLearner, query: string, facts: string[] = []): string {
  const lang = detectLang(query);

  // Every step below passes the RELEVANCE GATE (relevance.ts): an entry may answer only
  // if it is about EVERY topic word of the question — one shared word is not enough.
  // Nothing relevant → '' → the web / the model / an honest "I don't know" answers.

  // 1) "Build me a website / page / app" → emit a complete, working template offline.
  const recipe = findRecipe(query);
  if (recipe && coversQuery(query, recipe.title, recipe.stack, recipe.summary, recipe.match.join(' '), recipe.steps.join(' '))) {
    return renderRecipe(recipe);
  }

  // 2) Programming question → a verbatim snippet + the official source URL.
  // (title + tech + HU alt words only — identifiers inside the code don't make it relevant)
  const snippet = findSnippet(query, (s) => coversQuery(query, s.title, s.tech, (s.alt ?? []).join(' ')));
  if (snippet) {
    const lead = lang === 'hu' ? 'Tessék, egy működő példa' : 'Here is a working example';
    return `${lead} — ${snippet.title}:\n${snippet.code}\nSource: ${snippet.source}`;
  }

  // 3) General-knowledge question → a clean, whole sentence in the user's language.
  const known = findKnowledge(query, lang);
  if (known) return known;

  // 4) A learned/seeded Q→A recall (clean whole sentence).
  const recalled = learner.recall(query)?.trim();
  if (recalled && !isPersonal(recalled)) return recalled; // PRIVACY: never recall personal data

  // 5) A relevant personal fact, wrapped in a natural sentence frame.
  const fact = facts.map((f) => f.trim()).find((f) => f && coversQuery(query, f));
  if (fact) {
    const src = findSource(query);
    const base = frameFact(fact, lang);
    return src ? `${base}\nSource: ${src.title} — ${src.url}` : base;
  }

  // 6) Something learned from the WEB earlier (3.b) → answer from it + the source link.
  const web = topCoveringWebDoc(query);
  if (web && coversQuery(query, web.title, web.snippet)) {
    const lead = lang === 'hu' ? 'Amit erről a neten találtam' : 'Here is what I found on the web';
    return `${lead}: ${web.snippet}\nSource: ${web.title} — ${web.url}`;
  }

  // 7) Last resort: a known technology → recommend the official docs — only when the
  //    question is about that technology itself ("python docs"), not about a detail
  //    of it ("how do I reverse a string in python" → the model answers that).
  const src = findSource(query, (s) => coversQuery(query, s.title, s.tech, s.topics.join(' ')));
  if (src) {
    const lead = lang === 'hu' ? 'Erről a hivatalos dokumentációban olvashatsz' : 'You can read about this in the official docs';
    return `${lead}: ${src.title} — ${src.url}`;
  }

  // Nothing clean to say — return '' so the arbiter falls back to a model.
  // (We intentionally do NOT return raw Markov babble here.)
  return '';
}

/**
 * The OFFLINE ask-bar answer (no API, no model): a clean, RELEVANT sentence from what
 * the brain KNOWS (knowledge base, learned Q→A, web facts, personal facts) — never a
 * Markov walk. Returns '' when the brain has nothing relevant (the caller then shows a
 * gentle "still learning"). The old word-association list ("…connects to: compatible,
 * clear, function") is gone: neighbour words are noise, not an answer.
 */
export function answerOffline(learner: BrainLearner, query: string, facts: string[] = []): string {
  return composeLocalAnswer(learner, query, facts);
}
