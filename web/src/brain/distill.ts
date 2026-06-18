// distill.ts — H2 of the hybrid (brain + Ollama): MODEL → BRAIN distillation.
// After every model answer the brain learns from it, so next time it can answer the
// same thing OFFLINE, on its own — autonomy rises, model-dependence falls:
//   • the full answer grows the vocabulary + associations (observe),
//   • the query → KEY-ESSENCE of the answer is stored as a clean Q→A (recall returns a
//     tidy sentence later, not the whole verbose model dump),
//   • a counter feeds the /brain "learned from model" readout.
// Offline knowledge distillation: the small local model teaches our growing brain.
import type { BrainLearner } from './learn';
import { extractKeyContent } from '../autolearn';

let distilled = 0;
/** How many model answers the brain has distilled this session (for the readout). */
export function distilledCount(): number {
  return distilled;
}

/**
 * Distil one model answer into the brain. `query` is the user's question, `answer`
 * the model's reply. Safe to call after any model turn; cheap and incremental.
 */
export function distillFromModel(learner: BrainLearner, query: string, answer: string): void {
  const a = answer.trim();
  if (!a || a.length < 8) return;
  // 1) the full answer grows vocabulary + word→word associations
  learner.observe(a, 'distill:model');
  // 2) store the query → clean essence as a recallable Q→A (so a later offline answer
  //    is a tidy sentence, not the whole reply). Falls back to a trimmed answer.
  let essence = '';
  try {
    essence = extractKeyContent(a, query, { maxSentences: 3, maxChars: 480 }).trim();
  } catch {
    essence = '';
  }
  if (!essence) essence = a.slice(0, 480);
  learner.observeTurn(query, essence, 'distill:model');
  distilled++;
}
