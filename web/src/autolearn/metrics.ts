// metrics.ts — track WHERE each answer comes from (brain / web / model) so we can
// show the brain "getting smarter" over time: as it learns, the brain-hit-rate
// should climb. localStorage-backed, tiny, never throws.
export type AnswerSource = 'brain' | 'web' | 'model';

const KEY = 'auri.autolearn.metrics';

interface Counts {
  brain: number;
  web: number;
  model: number;
}

export interface BrainMetrics extends Counts {
  total: number;
  /** Fraction answered offline from the brain, 0..1 — the "smartness" signal. */
  brainHitRate: number;
  /** Fraction that needed a web search, 0..1. */
  webRate: number;
  updatedAt: string;
}

function read(): Counts {
  try {
    const c = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<Counts>;
    return { brain: c.brain ?? 0, web: c.web ?? 0, model: c.model ?? 0 };
  } catch {
    return { brain: 0, web: 0, model: 0 };
  }
}

function write(c: Counts): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(c));
  } catch {
    /* storage blocked */
  }
}

/** Record one answered turn by where the answer came from. Safe: never throws. */
export function recordAnswer(source: AnswerSource): void {
  const c = read();
  c[source] += 1;
  write(c);
}

/** Current snapshot incl. the brain hit-rate (the "getting smarter" curve). */
export function getMetrics(): BrainMetrics {
  const c = read();
  const total = c.brain + c.web + c.model;
  const div = total || 1;
  return {
    ...c,
    total,
    brainHitRate: c.brain / div,
    webRate: c.web / div,
    updatedAt: new Date().toISOString(),
  };
}

export function resetMetrics(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
}
