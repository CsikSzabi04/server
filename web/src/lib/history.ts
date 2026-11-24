// history.ts — keep a chat request inside the proxy's limits (api/_guard.ts:
// MAX_MESSAGES 100, MAX_PROMPT_CHARS 120 000). The app sends the whole conversation
// with every question, so a long chat would otherwise start failing with HTTP 400.
//
// Rule: every system message is kept (persona, memory, grounding), the NEWEST message
// is always kept whole (never silently truncate what the user just sent — if it alone
// is too big, the server answers with a clear "prompt too large" error), and the
// oldest turns are dropped first until the rest fits.
import type { ChatMessage } from './api';

export const HISTORY_MAX_MESSAGES = 60; // comfortably under the proxy's 100
export const HISTORY_MAX_CHARS = 90_000; // comfortably under the proxy's 120 000

export function fitHistory(
  msgs: ChatMessage[],
  maxMessages = HISTORY_MAX_MESSAGES,
  maxChars = HISTORY_MAX_CHARS,
): ChatMessage[] {
  const system = msgs.filter((m) => m.role === 'system');
  const turns = msgs.filter((m) => m.role !== 'system');
  if (turns.length === 0) return system;

  let budget = maxChars - system.reduce((s, m) => s + m.content.length, 0);
  const slots = Math.max(1, maxMessages - system.length);
  const newest = turns[turns.length - 1];
  const kept: ChatMessage[] = [newest];
  budget -= newest.content.length;

  for (let i = turns.length - 2; i >= 0 && kept.length < slots; i--) {
    const m = turns[i];
    if (m.content.length > budget) break; // older turns no longer fit → drop them
    budget -= m.content.length;
    kept.unshift(m);
  }
  // Don't open the window on a dangling assistant reply without its question.
  while (kept.length > 1 && kept[0].role === 'assistant') kept.shift();
  return [...system, ...kept];
}
