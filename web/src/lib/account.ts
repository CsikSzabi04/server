// account.ts — the signed-in user's GDPR self-service (SECURITY.md §16, H-6):
//   exportAllMyData()  — right of access + data portability (art. 15, 20): everything
//                        we store about the account, as one JSON file.
//   deleteMyAccount()  — right to erasure (art. 17): deletes the account and, through
//                        ON DELETE CASCADE, all of its rows; then wipes this browser's
//                        per-user local copies. Needs supabase/delete_account.sql.
// Both act ONLY on the caller's own account: the id comes from the verified session,
// and the database enforces it again (RLS / auth.uid()).
import { supabase } from './supabase';
import { scopedKey } from './storageScope';
import { idbDel } from '../brain-bridge/idb';
import { forgetLocalBrain } from '../brain/brainStore';
import { clearSearchCache } from '../autolearn/searchCache';
import { wipeStage6Local } from './stage6Wipe';

const PAGE = 1000;

async function allRows(table: string, userId: string, order: string): Promise<unknown[]> {
  if (!supabase) return [];
  const out: unknown[] = [];
  for (let from = 0; ; from += PAGE) {
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('user_id', userId)
      .order(order, { ascending: true })
      .range(from, from + PAGE - 1);
    if (error) throw new Error(`${table}: ${error.message}`);
    out.push(...(data ?? []));
    if (!data || data.length < PAGE) break;
  }
  return out;
}

/** Everything stored for the signed-in account, as a downloadable JSON Blob. */
export async function exportAllMyData(): Promise<Blob> {
  if (!supabase) throw new Error('Supabase is not configured.');
  const { data: u } = await supabase.auth.getUser();
  const user = u.user;
  if (!user) throw new Error('Sign in to export your account data.');
  const [profiles, conversations, messages, memories, brain] = await Promise.all([
    allRows('profiles', user.id, 'user_id'),
    allRows('conversations', user.id, 'created_at'),
    allRows('messages', user.id, 'created_at'),
    allRows('memories', user.id, 'created_at'),
    allRows('brain_state', user.id, 'user_id').catch(() => []), // table is optional
  ]);
  const dump = {
    exportedAt: new Date().toISOString(),
    service: 'AuriGPT',
    account: { id: user.id, email: user.email, createdAt: user.created_at, lastSignInAt: user.last_sign_in_at },
    profile: profiles[0] ?? null,
    conversations,
    messages,
    memories,
    brainState: brain[0] ?? null,
  };
  return new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
}

/**
 * Permanently delete the signed-in account and all of its data.
 * Returns null on success, or a human-readable error.
 */
export async function deleteMyAccount(): Promise<string | null> {
  if (!supabase) return 'Supabase is not configured.';
  const { data: u } = await supabase.auth.getUser();
  const uid = u.user?.id;
  if (!uid) return 'You are not signed in.';

  const { error } = await supabase.rpc('delete_my_account');
  if (error) {
    return /function|schema cache|does not exist/i.test(error.message)
      ? 'Account deletion is not set up on the server yet (run web/supabase/delete_account.sql).'
      : error.message;
  }

  // The account is gone server-side; now remove this browser's per-user copies.
  try {
    await forgetLocalBrain(uid);
    await idbDel(scopedKey('auri.brainWeb', uid));
    localStorage.removeItem(scopedKey('auri.projects', uid));
    localStorage.removeItem(scopedKey('auri.codeLearnings', uid));
    localStorage.removeItem(scopedKey('auri.modelPrefs', uid)); // incl. the user's BYO keys
    clearSearchCache();
    await wipeStage6Local();
  } catch {
    /* best effort — the server-side deletion already happened */
  }
  await supabase.auth.signOut().catch(() => undefined); // the session is invalid now anyway
  return null;
}
