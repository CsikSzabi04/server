// selfStudy.ts — H4 of the hybrid: the brain STUDIES ON ITS OWN, using the local
// model as a tutor. While idle, it picks a topic it should deepen, the bridge asks
// the model about it, and the answer is distilled back into the brain (H2). Over time
// the brain deepens real topics and connects concepts WITHOUT the user asking —
// "builds itself". Bounded (a finite rotating pool) + rate-limited + flag-gated.
import type { BrainLearner } from './learn';

// High-value, REAL topics to deepen (programming + general). The model is asked to
// explain each and what it connects to → grows knowledge + associations.
const STUDY_SEEDS = [
  'javascript', 'typescript', 'react', 'node', 'python', 'java', 'kotlin', 'php', 'sql', 'mysql', 'oracle',
  'vite', 'docker', 'kubernetes', 'git', 'rest api', 'graphql', 'http', 'dns', 'json', 'regex', 'authentication',
  'encryption', 'machine learning', 'neural network', 'database', 'orm', 'express', 'django', 'flask', 'spring',
  'tailwind', 'webpack', 'linux', 'cloud computing', 'ci cd', 'unit testing', 'async programming', 'recursion',
  'data structures', 'algorithms', 'binary search', 'hash table', 'web security', 'caching', 'websockets',
  // general knowledge to broaden
  'gravity', 'evolution', 'photosynthesis', 'the solar system', 'electricity', 'the human brain', 'climate',
  'democracy', 'the economy', 'music theory', 'world history', 'geography', 'mathematics', 'probability',
];

const studied = new Set<string>();
let cursor = 0;

/** The next topic the brain should study (rotates the pool, then revisits). Returns
 *  null only if the pool is empty. */
export function nextStudyTopic(_learner: BrainLearner): string | null {
  if (STUDY_SEEDS.length === 0) return null;
  // one full pass of fresh topics first, then start revisiting (deepening) from the top
  for (let i = 0; i < STUDY_SEEDS.length; i++) {
    const t = STUDY_SEEDS[(cursor + i) % STUDY_SEEDS.length];
    if (!studied.has(t)) {
      cursor = (cursor + i + 1) % STUDY_SEEDS.length;
      studied.add(t);
      return t;
    }
  }
  const t = STUDY_SEEDS[cursor % STUDY_SEEDS.length];
  cursor = (cursor + 1) % STUDY_SEEDS.length;
  return t;
}

/** Build the tutor question the model should answer for a study topic. */
export function studyQuestion(topic: string): string {
  return `Briefly explain ${topic}: what it is, what it is used for, and what it commonly works or connects with. 2-4 sentences.`;
}
