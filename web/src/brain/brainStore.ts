// BRAIN persistence — owned by AI-3 (BODY). Implements the `BrainStore` contract
// (contracts.ts): the compact local-learner snapshot (BrainPersistState) is saved
// to a Supabase row when signed in (RLS-isolated, see supabase/brain_state.sql) and
// to IndexedDB for guests (no ~5 MB localStorage cap → the large 200k-vocab brain
// fits), always mirrored locally so a refresh paints instantly.
//
// AI-1's useBrainLearning can swap its loadLS()/saveLS() for brainStore.load()/save()
// (or the brain-bridge/idb helpers) — same `BrainPersistState` shape, same key
// ('auri.brainLearn'); migrateFromLocalStorage() carries existing guest progress over.
import type { BrainPersistState, BrainStore } from './contracts';
import { supabase } from '../lib/supabase';
import { idbSet, idbDel, migrateFromLocalStorage } from '../brain-bridge/idb';

// Shared with the learner's existing local key so the swap loses no guest data.
const LS_KEY = 'auri.brainLearn';

function isPersistState(v: unknown): v is BrainPersistState {
  return !!v && typeof v === 'object' && 'vocab' in (v as Record<string, unknown>);
}

// Guest persistence lives in IndexedDB (no ~5 MB cap), migrating any existing
// localStorage snapshot on first read so nothing is lost.
async function localGet(): Promise<BrainPersistState | null> {
  const v = await migrateFromLocalStorage<BrainPersistState>(LS_KEY);
  return isPersistState(v) ? v : null;
}

async function localSet(state: BrainPersistState): Promise<void> {
  await idbSet(LS_KEY, state);
}

async function load(userId: string | null): Promise<BrainPersistState | null> {
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('brain_state')
      .select('state')
      .eq('user_id', userId)
      .maybeSingle();
    if (error || !data || !isPersistState(data.state)) return localGet(); // fall back to local mirror
    return data.state as BrainPersistState;
  }
  return localGet();
}

/** Write the snapshot through immediately (IndexedDB mirror + Supabase when signed in). */
async function writeNow(userId: string | null, state: BrainPersistState): Promise<void> {
  await localSet(state); // local mirror in IndexedDB (no 5 MB cap)
  if (userId && supabase) {
    await supabase
      .from('brain_state')
      .upsert(
        { user_id: userId, state, updated_at: new Date().toISOString() },
        { onConflict: 'user_id' },
      );
  }
}

// Debounced save: observe() fires every turn and the snapshot can be large (200k+
// vocab), so we coalesce rapid writes — the latest state wins after a short idle —
// instead of serialising + writing to IndexedDB/Supabase on every single turn.
const SAVE_DEBOUNCE_MS = 1500;
let pending: { userId: string | null; state: BrainPersistState } | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;

async function flush(): Promise<void> {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (!pending) return;
  const { userId, state } = pending;
  pending = null;
  await writeNow(userId, state);
}

async function save(userId: string | null, state: BrainPersistState): Promise<void> {
  pending = { userId, state };
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    timer = null;
    void flush();
  }, SAVE_DEBOUNCE_MS);
}

// Don't lose the last turns: flush when the tab is hidden / about to close.
if (typeof window !== 'undefined') {
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') void flush();
  });
  window.addEventListener('pagehide', () => void flush());
}

async function exportJSON(userId: string | null): Promise<BrainPersistState | null> {
  await flush(); // ensure any pending write lands before we read it back
  return load(userId);
}

async function importJSON(userId: string | null, data: BrainPersistState): Promise<void> {
  await writeNow(userId, data); // user-triggered + rare → persist immediately
}

/** The BrainStore implementation AI-1's useBrainLearning consumes. */
export const brainStore: BrainStore = { load, save, exportJSON, importJSON };

/** Convenience: wipe the saved learner from both stores (not part of the contract). */
export async function clearBrainState(userId: string | null): Promise<void> {
  await idbDel(LS_KEY);
  if (userId && supabase) {
    await supabase.from('brain_state').delete().eq('user_id', userId);
  }
}
