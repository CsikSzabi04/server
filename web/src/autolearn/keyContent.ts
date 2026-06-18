// keyContent.ts — extractive "important content" picker: from a web result's text
// (snippet or full page), keep the most informative sentences (keyword-dense +
// query-relevant) so the brain learns the ESSENCE, not raw/boilerplate text.
// Pure, no deps. Directly deepens "save the important data/words".
import { extractKeywords } from '../lib/memory';

export interface KeyContentOptions {
  /** Max sentences to keep. Default 3. */
  maxSentences?: number;
  /** Max total characters. Default 480. */
  maxChars?: number;
}

function splitSentences(text: string): string[] {
  return text
    .replace(/\s+/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 24);
}

/** The most informative sentences from `text` for `query`, in original order. */
export function keySentences(text: string, query: string, opts: KeyContentOptions = {}): string[] {
  const maxSentences = opts.maxSentences ?? 3;
  const maxChars = opts.maxChars ?? 480;
  const qk = new Set(extractKeywords(query, 12));

  const scored = splitSentences(text).map((s, i) => {
    const kws = extractKeywords(s, 20);
    let overlap = 0;
    for (const k of kws) if (qk.has(k)) overlap++;
    // relevance to the query + general informativeness + small lead bonus
    return { s, i, score: overlap * 4 + Math.min(kws.length, 12) + (i === 0 ? 2 : 0) };
  });

  const picked: { s: string; i: number }[] = [];
  let chars = 0;
  for (const item of [...scored].sort((a, b) => b.score - a.score)) {
    if (picked.length >= maxSentences) break;
    if (chars + item.s.length > maxChars) continue;
    picked.push(item);
    chars += item.s.length;
  }
  return picked.sort((a, b) => a.i - b.i).map((p) => p.s);
}

/** Condensed, informative content for a query (joined key sentences). */
export function extractKeyContent(text: string, query: string, opts: KeyContentOptions = {}): string {
  const sents = keySentences(text, query, opts);
  return sents.length ? sents.join(' ') : text.replace(/\s+/g, ' ').trim().slice(0, opts.maxChars ?? 480);
}
