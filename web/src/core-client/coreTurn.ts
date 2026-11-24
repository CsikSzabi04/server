// coreTurn — one chat turn through the local Auri Core (owner: AI-3, P1; spec 01/03 §7.4, 01/04 §5 A).
// Used by App.send() as step 0: when the `auri.brain.core` switch is on and the Core answers,
// its reply is shown; on null (off / unreachable / paused / error) the old chain runs unchanged.
// Grounding: the Core's own verified knowledge (`/recall`, T0 + own T1) goes in as context, so the
// local model answers from what Auri already knows instead of from memory alone.

import { coreAnswer, coreRecall, isCoreEnabled } from './coreClient';

export { isCoreEnabled };

const RECALL_K = 3;
const REL_SCORE = 0.6; // keep hits ≥ 60% of the best one (stray matches like 'mi' → 'meta' score ~40%)

function guessLang(text: string): 'hu' | 'en' | undefined {
  if (/[áéíóöőúüű]/i.test(text) || /\b(mi|mit|hogy|hogyan|miért|melyik|van|egy|az|és)\b/i.test(text)) return 'hu';
  if (/\b(what|how|why|which|is|the|and)\b/i.test(text)) return 'en';
  return undefined; // the Core detects it itself
}

/** The Core's answer text, or null → the caller falls back to the browser brain / web / model. */
export async function coreTurn(text: string, signal?: AbortSignal): Promise<string | null> {
  if (!isCoreEnabled()) return null;
  const lang = guessLang(text);
  const all = await coreRecall(text.slice(0, 500), RECALL_K, lang);
  const best = all[0]?.score ?? 0;
  const context = all
    .filter((h) => h.score >= best * REL_SCORE)
    .map((h) => `${h.title}: ${h.body.replace(/\n+Kulcsszavak:.*$/s, '')}`.slice(0, 1200));
  const res = await coreAnswer({ text, mode: 'chat', context }, signal);
  if (!res || res.error || !res.text.trim()) return null;
  return res.text;
}
