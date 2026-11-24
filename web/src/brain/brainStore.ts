// BRAIN persistence — owned by AI-3 (BODY). Implements the `BrainStore` contract
// (contracts.ts): the compact local-learner snapshot (BrainPersistState) is saved
// to a Supabase row when signed in (RLS-isolated, see supabase/brain_state.sql) and
// to IndexedDB (no ~5 MB localStorage cap → the large vocab brain fits), mirrored
// locally so a refresh paints instantly.
//
// PRIVACY (SECURITY.md §4.4): the local mirror is keyed PER IDENTITY —
//   guest           → 'auri.brainLearn.guest'
//   signed-in user  → 'auri.brainLearn.u.<userId>'
// so a logged-out screen (or another account on the same browser) can never load a
// signed-in user's brain. Older builds used ONE shared key ('auri.brainLearn') for
// everybody; that legacy snapshot is handed once to the first account that signs in
// on this device and is never read as a guest. On sign-out the user's local mirror
// is deleted — but only once Supabase is confirmed to hold their copy, so nothing
// is lost when the brain_state table isn't set up.
import type { BrainPersistState, BrainStore } from './contracts';
import { supabase } from '../lib/supabase';
import { idbGet, idbSet, idbDel } from '../brain-bridge/idb';
import { scopedKey } from '../lib/storageScope';

const BASE = 'auri.brainLearn';
const LEGACY_KEY = BASE; // pre-scoping shared key (IndexedDB and/or localStorage)
const CLAIMED_FLAG = `${BASE}.claimed`;
const keyFor = (userId: string | null): string => (userId ? scopedKey(BASE, userId) : `${BASE}.guest`);

function isPersistState(v: unknown): v is BrainPersistState {
  return !!v && typeof v === 'object' && 'vocab' in (v as Record<string, unknown>);
}

/** Hand the unattributable legacy snapshot to the first account that signs in here. */
async function claimLegacy(userId: string): Promise<void> {
  try {
    if (localStorage.getItem(CLAIMED_FLAG)) return;
  } catch {
    return;
  }
  const legacy = await idbGet<BrainPersistState>(LEGACY_KEY);
  if (isPersistState(legacy) && !isPersistState(await idbGet(keyFor(userId)))) await idbSet(keyFor(userId), legacy);
  await idbDel(LEGACY_KEY);
  try {
    localStorage.setItem(CLAIMED_FLAG, '1');
  } catch {
    /* storage blocked */
  }
}

async function localGet(userId: string | null): Promise<BrainPersistState | null> {
  const v = await idbGet<BrainPersistState>(keyFor(userId));
  return isPersistState(v) ? v : null;
}

async function localSet(userId: string | null, state: BrainPersistState): Promise<void> {
  await idbSet(keyFor(userId), state);
}

// Identities whose local mirror was just wiped (sign-out / account deletion). A save
// that was still debounced or already in flight must not re-create it afterwards.
// Cleared again when that identity loads (signs in) next time.
const forgotten = new Set<string>();

async function load(userId: string | null): Promise<BrainPersistState | null> {
  if (userId) forgotten.delete(userId);
  if (userId) await claimLegacy(userId);
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('brain_state')
      .select('state')
      .eq('user_id', userId)
      .maybeSingle();
    // fall back to THIS user's own local mirror only — never another identity's
    if (error || !data || !isPersistState(data.state)) return localGet(userId);
    return data.state as BrainPersistState;
  }
  return localGet(userId);
}

/** Write the snapshot through immediately (local mirror + Supabase when signed in). */
async function writeNow(userId: string | null, state: BrainPersistState): Promise<void> {
  if (userId && forgotten.has(userId)) return; // signed out / deleted meanwhile → drop it
  await localSet(userId, state);
  if (userId && forgotten.has(userId)) {
    await idbDel(keyFor(userId)); // the wipe happened while we were writing → undo our write
    return;
  }
  if (userId && supabase) {
    await supabase
      .from('brain_state')
      .upsert(
        { user_id: userId, state, updated_at: new Date().toISOString() },
        { onConflict: 'user_id' },
      );
  }
}

// Debounced save: observe() fires every turn and the snapshot can be large, so we
// coalesce rapid writes — the latest state wins after a short idle — instead of
// serialising + writing to IndexedDB/Supabase on every single turn.
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
  await idbDel(keyFor(userId));
  if (userId && supabase) {
    await supabase.from('brain_state').delete().eq('user_id', userId);
  }
}

/**
 * Sign-out step 1 — call while the session is STILL valid: write any pending save
 * to Supabase, then report whether Supabase really holds this user's brain (only
 * then is it safe to delete the local mirror in step 2).
 */
export async function prepareBrainSignOut(userId: string): Promise<boolean> {
  await flush();
  if (!supabase) return false;
  const { data, error } = await supabase.from('brain_state').select('user_id').eq('user_id', userId).maybeSingle();
  return !error && !!data;
}

/** Sign-out step 2 / account deletion — remove the user's local brain mirror from this
 *  browser, and make sure no pending or in-flight save can write it back. */
export async function forgetLocalBrain(userId: string): Promise<void> {
  forgotten.add(userId);
  if (pending?.userId === userId) {
    pending = null;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }
  await idbDel(keyFor(userId));
}
