// useBrainLearning — exposes the BrainState (stage, vocab, associations, autonomy)
// for the /brain view, grows the local learner from chat turns, and SEEDS a fresh
// brain on first load. Persistence now goes through AI-3's async brainStore
// (IndexedDB for guests — no ~5 MB cap → the large 200k-vocab brain fits — and
// Supabase when signed in), so the brain survives refresh and scales.
//
// One SHARED learner backs the whole app (both useBrainLearning and useBrainGraph),
// so there is a single brain. A seeded learner is available SYNCHRONOUSLY at once
// (the view paints immediately); the persisted brain hydrates right after, async.
import { useCallback, useEffect, useMemo, useSyncExternalStore } from 'react';
import { useAuth } from '../hooks/useAuth';
import { BrainLearner, deriveStage } from './learn';
import { SEED_VERSION, seedBaseBrain, applyBaseSeed, seedIngestedCorpora } from './seedCorpus';
import { composeLocalAnswer, answerOffline } from './answer';
import { brainStore } from './brainStore';
import { programmingSeqs, generalSeqs } from './seed/bulkVocab';
import { selfBuildConnected, selfBuildIsolated, selfBuildData } from './seed/selfBuild';
import { ingestWeb, brainCovers } from './web';
import { buildBrainContext } from './grounding';
import { distillFromModel, distilledCount } from './distill';
import { nextStudyTopic } from './selfStudy';
import { loadWebDocs } from './webStore';
import type { Memory } from '../lib/memory';
import { trainStage6, stage6Status } from './stage6/net';
import type { BrainLearningResult, BrainState, WebHit, Stage6Status } from './contracts';

// Stage 6 (optional in-browser neural net) — default ON since the user asked for it;
// disable by setting localStorage['auri.brain.stage6'] = '0'. Trains once (persisted).
const STAGE6_KEY = 'auri.brain.stage6';
function stage6Enabled(): boolean {
  try {
    return localStorage.getItem(STAGE6_KEY) !== '0';
  } catch {
    return true;
  }
}

// Large procedural vocabulary targets (the user's goal: ~700k programming + ~300k
// general). Seeded in CHUNKS across idle ticks so the UI never freezes; regenerated
// each session (NOT persisted — see learn.toState()), so saves stay small and fast.
const BULK_PROGRAMMING = 1_000_000;
const BULK_GENERAL = 300_000;
const BULK_CHUNK = 4_000; // sequences ingested per idle tick (~24k tokens)

// ── shared singleton + tiny external store (so both hooks re-render together) ──
let learnerSingleton: BrainLearner | null = null;
let version = 0;
let hydratedFor: string | null | undefined = undefined; // which userId is loaded
let hydrating = false;
const listeners = new Set<() => void>();
const subscribe = (cb: () => void): (() => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};
const getVersion = (): number => version;
const emit = (): void => {
  version++;
  for (const l of listeners) l();
};

/** A seeded learner is ALWAYS available immediately (no await) so the view paints
 *  at once; the persisted brain hydrates right after. Shared across hooks. */
export function initLearner(): BrainLearner {
  if (!learnerSingleton) {
    const l = new BrainLearner();
    seedBaseBrain(l); // never empty before hydration
    learnerSingleton = l;
  }
  return learnerSingleton;
}

function persist(userId: string | null): void {
  if (!learnerSingleton) return;
  void brainStore.save(userId, { ...learnerSingleton.toState(), seedVersion: SEED_VERSION });
}

// ── chunked bulk-vocabulary seeding (non-blocking) ─────────────────────────────
let bulkStarted = false;
// NOTE: use setTimeout, NOT requestIdleCallback — the /brain page runs a continuous
// 3D animation (rAF), so the main thread is never "idle" and rIC callbacks starve.
// setTimeout still fires between frames, so the bulk vocabulary actually loads.
const schedule = (fn: () => void): void => {
  setTimeout(fn, 0);
};

/** Seed the large procedural vocabulary in small chunks across idle ticks so the
 *  word/link counters climb without ever freezing the UI. Runs once per session. */
function startBulkSeed(): void {
  if (bulkStarted) return;
  bulkStarted = true;
  const l = initLearner();
  const progGen = programmingSeqs(BULK_PROGRAMMING);
  const genGen = generalSeqs(BULK_GENERAL);
  let phase: 'prog' | 'gen' = 'prog';
  let ticks = 0;
  const step = (): void => {
    const gen = phase === 'prog' ? progGen : genGen;
    const src = phase === 'prog' ? 'bulk:prog' : 'bulk:general';
    let n = 0;
    let exhausted = false;
    while (n < BULK_CHUNK) {
      const r = gen.next();
      if (r.done) {
        exhausted = true;
        break;
      }
      l.ingestTokens(r.value, src);
      n++;
    }
    // Emit (→ heavy graph rebuild) only at phase end, so the heavy build doesn't
    // starve the fill — the `words` count then reaches its TRUE value fast.
    if (++ticks % 1000 === 0 || exhausted) emit();
    if (exhausted) {
      if (phase === 'prog') {
        phase = 'gen';
        schedule(step);
      }
      // else: all done
    } else {
      schedule(step);
    }
  };
  schedule(step);
}

// ── self-build: the brain keeps building itself in the background ──────────────
// Adds VISIBLE concept nodes (count≥2) in two kinds the user wants on /brain —
// CONNECTED clusters (wired to existing hubs) and ISOLATED "knowledge balls" — plus
// a large count==1 data stream. All 'bulk:self' tagged → not persisted, regenerated.
let selfBuildStarted = false;
const SB_CONNECTED = 13_000; // visible, connected concept nodes (dense brain body)
const SB_ISOLATED = 12_000; // visible, isolated "knowledge balls" filling the volume
const SB_DATA = 900_000; // count==1 vocabulary (the requested extra knowledge)
function startSelfBuild(): void {
  if (selfBuildStarted) return;
  selfBuildStarted = true;
  const l = initLearner();
  const conn = selfBuildConnected(SB_CONNECTED);
  const iso = selfBuildIsolated(SB_ISOLATED);
  const data = selfBuildData(SB_DATA);
  let phase: 'conn' | 'iso' | 'data' = 'conn';
  let ticks = 0;
  const step = (): void => {
    let exhausted = false;
    if (phase === 'conn') {
      for (let c = 0; c < 500; c++) {
        const r = conn.next();
        if (r.done) { exhausted = true; break; }
        l.ingestTokens(r.value, 'bulk:self'); // twice → count≥2 (visible) + edges (connected)
        l.ingestTokens(r.value, 'bulk:self');
      }
    } else if (phase === 'iso') {
      for (let c = 0; c < 1_500; c++) {
        const r = iso.next();
        if (r.done) { exhausted = true; break; }
        l.ingestTokens([r.value], 'bulk:self'); // twice → count≥2 (visible), no edge (isolated ball)
        l.ingestTokens([r.value], 'bulk:self');
      }
    } else {
      for (let c = 0; c < 8_000; c++) {
        const r = data.next();
        if (r.done) { exhausted = true; break; }
        l.ingestTokens(r.value, 'bulk:self'); // count==1 vocabulary (the number)
      }
    }
    if (++ticks % 1000 === 0 || exhausted) emit(); // phase-end only → fill isn't starved
    if (exhausted) {
      if (phase === 'conn') { phase = 'iso'; schedule(step); }
      else if (phase === 'iso') { phase = 'data'; schedule(step); }
      // else: fully built
    } else {
      schedule(step);
    }
  };
  schedule(step);
}

/** Subscribe a component to brain changes (hydrate / observe / reset). */
export function useBrainVersion(): number {
  return useSyncExternalStore(subscribe, getVersion, getVersion);
}
/** Ensure the persisted brain is loaded for this user (idempotent; safe to call often). */
export function ensureHydrated(userId: string | null): void {
  void hydrateFor(userId);
}

/** Load the persisted brain (IndexedDB/Supabase) for this user and merge it in,
 *  then notify. Idempotent per userId; re-runs on login/logout. */
async function hydrateFor(userId: string | null): Promise<void> {
  if (hydratedFor === userId || hydrating) return;
  hydrating = true;
  try {
    await loadWebDocs(); // bring back web-learned facts (region:web) from IndexedDB
    const snap = await brainStore.load(userId);
    const l = BrainLearner.from(snap);
    // Seed a fresh brain; augment an out-of-date one (additive — never wipes learned data).
    const needSeed = (snap?.seedVersion ?? 0) < SEED_VERSION;
    if (needSeed) {
      if (l.vocabSize === 0) seedBaseBrain(l);
      else applyBaseSeed(l);
    }
    learnerSingleton = l;
    hydratedFor = userId;
    emit(); // paint with the curated (in-bundle) brain immediately
    // Heavy ingested corpora load lazily (dynamic import) AFTER first paint, and only
    // when (re)seeding — returning users already have them in the persisted snapshot.
    if (needSeed) {
      await seedIngestedCorpora(l);
    }
    if (l.assocSize > 4000) l.consolidate(); // M4: keep a large brain lean & fast
    void brainStore.save(userId, { ...l.toState(), seedVersion: SEED_VERSION });
    emit();
    startBulkSeed(); // fill the large procedural vocabulary in the background
    // self-build: the brain keeps growing itself (connected + isolated concept nodes
    // + more data) a few seconds after the initial bulk, so it visibly builds up.
    setTimeout(startSelfBuild, 5000);
    // Stage 6: train the optional in-browser neural net a few seconds later (after the
    // UI has settled), gated by a flag and guarded so it can never break the app.
    if (stage6Enabled()) setTimeout(() => void trainStage6(l, emit), 3500);
  } finally {
    hydrating = false;
  }
}

function stateOf(l: BrainLearner): BrainState {
  const vocab = l.vocabSize;
  const associations = l.assocSize;
  const chars = l.charCount;
  const qaPatterns = l.qaCount;
  const d = deriveStage(vocab, associations, l.trainSteps, chars, qaPatterns);
  // Stage 6 overrides the derived stage once the neural net is trained & ready.
  const s6 = stage6Status();
  const stage = s6.ready ? 6 : d.stage;
  const stageLabel = s6.ready ? 'Local network' : d.label;
  return {
    stage,
    stageLabel,
    vocab,
    chars,
    associations,
    qaPatterns,
    trainSteps: l.trainSteps,
    autonomyPct: d.autonomyPct,
    updatedAt: new Date().toISOString(),
  };
}

export function useBrainLearning(): BrainLearningResult {
  const auth = useAuth();
  const userId = auth.user?.id ?? null;
  // Re-render whenever the shared brain changes (hydrate/observe/reset/bulk-seed) and
  // DERIVE the live state from that version, so the word/link counters keep climbing
  // as the background bulk-seed grows the vocabulary (not a one-shot snapshot).
  const version = useSyncExternalStore(subscribe, getVersion, getVersion);
  const state = useMemo<BrainState>(() => stateOf(initLearner()), [version]);

  // hydrate the persisted brain once per user (and re-hydrate on login/logout)
  useEffect(() => {
    void hydrateFor(userId);
  }, [userId]);

  const observe = useCallback(
    (userText: string, assistantText: string) => {
      initLearner().observeTurn(userText, assistantText);
      persist(userId);
      emit(); // bumps version → state re-derives
    },
    [userId],
  );

  const reset = useCallback(() => {
    const fresh = new BrainLearner();
    seedBaseBrain(fresh); // back to the seeded baseline, not totally empty
    learnerSingleton = fresh;
    hydratedFor = userId;
    bulkStarted = false; // allow the bulk vocabulary to refill after a reset
    selfBuildStarted = false; // and let the brain rebuild itself
    persist(userId);
    emit();
    startBulkSeed();
    setTimeout(startSelfBuild, 5000);
  }, [userId]);

  // The brain's own statistical reply attempt (recall a Q→A, else Markov walk).
  const speak = useCallback((query: string) => initLearner().respond(query), []);
  const babble = useCallback((maxChars?: number) => initLearner().babble(maxChars), []);
  const recentWords = useCallback((limit?: number) => initLearner().recentWords(limit), []);
  // Local-brain answer: caller-supplied personal facts + the base brain's phrasing.
  const reply = useCallback(
    (query: string, facts?: string[]) => composeLocalAnswer(initLearner(), query, facts ?? []),
    [],
  );
  // Brain-first routing: is this already covered (and fresh) offline?
  const covers = useCallback(
    (query: string, facts?: string[]) => brainCovers(initLearner(), query, facts ?? []),
    [],
  );
  // Learn from web results (3.b): store source docs + grow vocab, then refresh.
  const learnWeb = useCallback(
    (query: string, hits: WebHit[], pages?: string[]) => {
      ingestWeb(initLearner(), query, hits, pages ?? []);
      persist(userId);
      emit(); // region:web nodes + counters refresh on /brain
    },
    [userId],
  );
  // Stage 6 neural-net status (learning curve, readiness) — recomputed on version bump.
  const stage6 = useCallback((): Stage6Status => stage6Status(), [version]);
  // Hybrid H1: the BRAIN KNOWLEDGE grounding block injected into the model's prompt.
  const ground = useCallback((query: string, memories: Memory[]) => buildBrainContext(initLearner(), query, memories), []);
  // Hybrid H2: distil a model answer into the brain (learn it for an offline answer next time).
  const distill = useCallback(
    (query: string, answer: string) => {
      distillFromModel(initLearner(), query, answer);
      persist(userId);
      emit();
      // H5: periodically refresh the Stage 6 net so it learns the newly distilled
      // knowledge (gentle — every 25 distillations, only if Stage 6 is enabled).
      if (stage6Enabled() && distilledCount() % 25 === 0) {
        setTimeout(() => void trainStage6(initLearner(), emit), 500);
      }
    },
    [userId],
  );
  // Hybrid H4: the next topic the brain should study on its own (tutored by the model).
  const studyTopic = useCallback(() => nextStudyTopic(initLearner()), []);
  // Offline ask-bar: a clean, topic-relevant sentence from what the brain knows (+ links),
  // never a random Markov walk.
  const ask = useCallback((query: string) => answerOffline(initLearner(), query, []), []);

  return { state, observe, reset, speak, babble, recentWords, reply, covers, learnWeb, stage6, ground, distill, studyTopic, ask };
}
