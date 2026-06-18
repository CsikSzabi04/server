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
import { findSnippet } from './seed/programmingCurated';
import { findSource } from './seed/sources';
import { findRecipe, renderRecipe } from './seed/recipes';
import { findKnowledge } from './seed/knowledge';
import { topCoveringWebDoc } from './webStore';

/** Top personal facts / doc snippets relevant to the query (read-only over memory). */
export function pickFacts(memories: Memory[], query: string, n = 3): string[] {
  const qk = new Set(extractKeywords(query, 12));
  return memories
    .filter((m) => m.kind === 'fact' || m.kind === 'summary' || m.kind === 'doc')
    .map((m) => {
      let score = (m.pinned ? 100 : 0) + (m.weight ?? 1);
      for (const k of extractKeywords(m.content, 10)) if (qk.has(k)) score += 5;
      return { m, score };
    })
    .sort((a, b) => b.score - a.score)
    .filter((x) => x.score >= 6)
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

  // 1) "Build me a website / page / app" → emit a complete, working template offline.
  const recipe = findRecipe(query);
  if (recipe) return renderRecipe(recipe);

  // 2) Programming question → a verbatim snippet + the official source URL.
  const snippet = findSnippet(query);
  if (snippet) {
    const lead = lang === 'hu' ? 'Tessék, egy működő példa' : 'Here is a working example';
    return `${lead} — ${snippet.title}:\n${snippet.code}\nSource: ${snippet.source}`;
  }

  // 3) General-knowledge question → a clean, whole sentence in the user's language.
  const known = findKnowledge(query, lang);
  if (known) return known;

  // 4) A learned/seeded Q→A recall (clean whole sentence).
  const recalled = learner.recall(query)?.trim();
  if (recalled) return recalled;

  // 5) A relevant personal fact, wrapped in a natural sentence frame.
  const fact = facts[0]?.trim();
  if (fact) {
    const src = findSource(query);
    const base = frameFact(fact, lang);
    return src ? `${base}\nSource: ${src.title} — ${src.url}` : base;
  }

  // 6) Something learned from the WEB earlier (3.b) → answer from it + the source link.
  const web = topCoveringWebDoc(query);
  if (web) {
    const lead = lang === 'hu' ? 'Amit erről a neten találtam' : 'Here is what I found on the web';
    return `${lead}: ${web.snippet}\nSource: ${web.title} — ${web.url}`;
  }

  // 7) Last resort: a known technology → recommend the official docs.
  const src = findSource(query);
  if (src) {
    const lead = lang === 'hu' ? 'Erről a hivatalos dokumentációban olvashatsz' : 'You can read about this in the official docs';
    return `${lead}: ${src.title} — ${src.url}`;
  }

  // Nothing clean to say — return '' so the arbiter falls back to a model.
  // (We intentionally do NOT return raw Markov babble here.)
  return '';
}

// Function words to drop from the association fallback (Markov neighbours are noisy).
const REL_STOP = new Set<string>(
  ('the and is are was a an of to in on at it or with that for be this you your they we ' +
    'egy az és van nem vagy mi hogy ezek ott itt is már csak offline brain').split(/\s+/),
);

/**
 * The OFFLINE ask-bar answer (no API, no model): a clean, topic-relevant sentence
 * assembled in microseconds from what the brain KNOWS — its knowledge base, learned
 * Q→A, web facts, and its word→word LINKS — NEVER a random Markov walk. Returns '' only
 * if the brain truly has nothing (the caller then shows a gentle "still learning").
 */
export function answerOffline(learner: BrainLearner, query: string, facts: string[] = []): string {
  // 1) the curated/learned clean answer (recipe/snippet/knowledge/recall/fact/web)
  const clean = composeLocalAnswer(learner, query, facts);
  if (clean) return clean;

  // 2) ASSOCIATION fallback — walk the links the brain learned for the query terms and
  //    state the related concepts (topic-relevant, clean — not gibberish).
  const lang = detectLang(query);
  const related = new Set<string>();
  for (const w of extractKeywords(query, 6)) {
    for (const n of learner.neighbors(w, 12)) {
      if (n.word.length >= 3 && !REL_STOP.has(n.word)) related.add(n.word);
    }
  }
  if (related.size >= 2) {
    const list = [...related].slice(0, 8).join(', ');
    return lang === 'hu'
      ? `Erről még tanulok, de amit eddig tudok, az ezekhez kapcsolódik: ${list}.`
      : `I'm still learning this, but from what I know it connects to: ${list}.`;
  }
  return '';
}
