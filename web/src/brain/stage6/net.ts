// stage6/net.ts — Stage 6 (BRAIN.md §20.6): a tiny, in-browser NEURAL next-word model
// (TensorFlow.js) that trains incrementally on what the learner already knows, for
// smoother phrasing than the Markov chain. Honest scope: a SMALL word-level predictor
// over the top-K vocabulary — not a GPT. Everything here is:
//   • LAZY: tfjs is loaded with dynamic import → 0 startup-bundle cost, no static dep.
//   • GUARDED: any failure (no WebGL, load error) just leaves Stage 6 inactive; the
//     rest of the brain (retrieval + knowledge + Markov) keeps working unchanged.
//   • PERSISTED: the trained model + its vocab survive reloads (IndexedDB), so it
//     trains once and is ready next time.
import type * as TF from '@tensorflow/tfjs';
import { idbGet, idbSet } from '../../brain-bridge/idb';
import type { BrainLearner } from '../learn';
import type { Stage6Status } from '../contracts';

const MODEL_URL = 'indexeddb://auri-stage6';
const VOCAB_KEY = 'auri.stage6.vocab';
const TOP_K = 1500; // model vocabulary = the K most frequent learned words
const MAX_PAIRS = 20_000; // training pairs sampled from the transition table
const EPOCHS = 8;

let status: Stage6Status = { available: false, training: false, ready: false, trainSteps: 0, loss: [], vocab: 0 };
export function stage6Status(): Stage6Status {
  return status;
}

let tf: typeof TF | null = null;
let model: TF.LayersModel | null = null;
let word2idx = new Map<string, number>();
let idx2word: string[] = [];

async function loadTf(): Promise<typeof TF | null> {
  if (tf) return tf;
  try {
    tf = await import('@tensorflow/tfjs');
    return tf;
  } catch {
    return null;
  }
}

function buildVocab(learner: BrainLearner): void {
  const top = [...learner.words.entries()]
    .filter(([, m]) => m.count > 1) // skip the count==1 bulk vocabulary
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, TOP_K)
    .map(([w]) => w);
  idx2word = top;
  word2idx = new Map(top.map((w, i) => [w, i]));
  status.vocab = top.length;
}

/** Sample (word → next-word) training pairs from the learner's transition table. */
function buildPairs(learner: BrainLearner): { xs: number[]; ys: number[] } {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const [a, nexts] of learner.transitions) {
    const ai = word2idx.get(a);
    if (ai === undefined) continue;
    for (const [b, count] of nexts) {
      const bi = word2idx.get(b);
      if (bi === undefined) continue;
      const reps = Math.min(3, count); // weight by strength, capped
      for (let r = 0; r < reps; r++) {
        xs.push(ai);
        ys.push(bi);
        if (xs.length >= MAX_PAIRS) return { xs, ys };
      }
    }
  }
  return { xs, ys };
}

function buildModel(t: typeof TF, vocab: number): TF.LayersModel {
  const m = t.sequential();
  m.add(t.layers.embedding({ inputDim: vocab, outputDim: 32, inputLength: 1 }));
  m.add(t.layers.flatten());
  m.add(t.layers.dense({ units: 64, activation: 'relu' }));
  m.add(t.layers.dense({ units: vocab, activation: 'softmax' }));
  m.compile({ optimizer: t.train.adam(0.01), loss: 'sparseCategoricalCrossentropy' });
  return m;
}

/**
 * Train (or resume) the Stage 6 net on the learner's corpus. Bounded + chunked by
 * tfjs's own yielding, so the UI stays responsive. Safe to call once on load.
 */
export async function trainStage6(learner: BrainLearner, onProgress?: () => void): Promise<void> {
  if (status.training) return;
  const t = await loadTf();
  if (!t) return; // tfjs unavailable → Stage 6 stays off, brain unaffected
  status.available = true;
  status.training = true;
  onProgress?.();
  try {
    buildVocab(learner);
    if (idx2word.length < 50) {
      status.training = false;
      onProgress?.();
      return; // not enough learned vocabulary yet
    }
    // Try to resume a persisted model whose vocab still matches.
    if (!model) {
      const savedVocab = await idbGet<string[]>(VOCAB_KEY);
      if (savedVocab && savedVocab.length === idx2word.length) {
        try {
          model = await t.loadLayersModel(MODEL_URL);
          idx2word = savedVocab;
          word2idx = new Map(savedVocab.map((w, i) => [w, i]));
          status.ready = true;
          status.trainSteps = EPOCHS;
        } catch {
          model = null;
        }
      }
    }
    if (!model) model = buildModel(t, idx2word.length);

    const { xs, ys } = buildPairs(learner);
    if (xs.length < 100) {
      status.training = false;
      onProgress?.();
      return;
    }
    const xt = t.tensor2d(xs, [xs.length, 1], 'int32');
    const yt = t.tensor1d(ys, 'int32');
    status.loss = [];
    await model.fit(xt, yt, {
      epochs: EPOCHS,
      batchSize: 256,
      shuffle: true,
      callbacks: {
        onEpochEnd: (_e: number, logs?: TF.Logs) => {
          status.trainSteps += 1;
          if (logs && typeof logs.loss === 'number') status.loss.push(Number(logs.loss.toFixed(4)));
          onProgress?.();
        },
      },
    });
    xt.dispose();
    yt.dispose();
    status.ready = true;
    // persist for next time (best-effort)
    try {
      await model.save(MODEL_URL);
      await idbSet(VOCAB_KEY, idx2word);
    } catch {
      /* persistence optional */
    }
  } catch {
    /* training failed → leave brain unaffected */
  } finally {
    status.training = false;
    onProgress?.();
  }
}

/** Predict the most likely next word after `word` (or null if the net can't). */
export function predictNextStage6(word: string): string | null {
  if (!tf || !model || !status.ready) return null;
  const ai = word2idx.get(word.toLowerCase());
  if (ai === undefined) return null;
  try {
    return tf.tidy(() => {
      const out = model!.predict(tf!.tensor2d([ai], [1, 1], 'int32')) as TF.Tensor;
      const idx = out.argMax(-1).dataSync()[0];
      return idx2word[idx] ?? null;
    });
  } catch {
    return null;
  }
}
