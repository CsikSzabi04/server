// Minimal Supabase auth hook: tracks the signed-in user and exposes
// sign-in / sign-up / sign-out. Email+password (works with Supabase's default
// email provider). Returns an error message string (or null on success).
import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import { supabase, isSupabaseConfigured } from '../lib/supabase';
import { setStorageScope } from '../lib/storageScope';
import { prepareBrainSignOut, forgetLocalBrain } from '../brain/brainStore';
import { clearSearchCache } from '../autolearn/searchCache';
import { resetGuestMemory } from '../lib/memStore';
import { reloadPrefsForIdentity } from '../lib/modelStore';
import { wipeStage6Local } from '../lib/stage6Wipe';

// Module-level so the many useAuth() instances agree on ONE identity transition.
let currentIdentity: string | null | undefined = undefined;
/** Switch every browser-local store to this identity. On a real change also wipe the
 *  guest's RAM memory (it belongs to nobody after a login / logout). */
function applyIdentity(uid: string | null): void {
  setStorageScope(uid);
  if (uid !== currentIdentity) {
    if (currentIdentity !== undefined) resetGuestMemory();
    currentIdentity = uid;
    reloadPrefsForIdentity(); // this identity's model choice + BYO keys
  }
}

export interface AuthApi {
  user: User | null;
  ready: boolean;
  configured: boolean;
  signIn: (email: string, password: string) => Promise<string | null>;
  /** `meta` (optional) is stored in the user's auth metadata — e.g. the terms/age consent record. */
  signUp: (email: string, password: string, meta?: Record<string, unknown>) => Promise<string | null>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthApi {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(!isSupabaseConfigured());

  useEffect(() => {
    if (!supabase) return;
    // The storage scope is set BEFORE React re-renders, so every local store reads
    // the new identity's keys from the very first render after a login / logout.
    void supabase.auth.getSession().then(({ data }) => {
      applyIdentity(data.session?.user?.id ?? null);
      setUser(data.session?.user ?? null);
      setReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      applyIdentity(session?.user?.id ?? null);
      setUser(session?.user ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  return {
    user,
    ready,
    configured: isSupabaseConfigured(),
    async signIn(email, password) {
      if (!supabase) return 'Supabase is not configured.';
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      return error?.message ?? null;
    },
    async signUp(email, password, meta) {
      if (!supabase) return 'Supabase is not configured.';
      const { error } = await supabase.auth.signUp({ email, password, options: meta ? { data: meta } : undefined });
      return error?.message ?? null;
    },
    // PRIVACY (SECURITY.md §4.4): after logout nothing of this account may remain
    // readable in the browser as a guest. 1) while the session is still valid, save
    // the pending brain to Supabase and confirm it's there; 2) sign out; 3) drop the
    // search cache (its keys are the user's queries) and — only if Supabase holds the
    // copy — the local brain mirror. Projects / web docs stay under the user's own key.
    async signOut() {
      const uid = user?.id ?? null;
      let brainSafeOnServer = false;
      if (uid) {
        try {
          brainSafeOnServer = await prepareBrainSignOut(uid);
        } catch {
          brainSafeOnServer = false;
        }
      }
      if (supabase) {
        // Offline / 5xx: the global sign-out returns an error and KEEPS the session. Then
        // end it at least on this device, so the guest state below is really a guest.
        const { error } = await supabase.auth.signOut();
        if (error) await supabase.auth.signOut({ scope: 'local' }).catch(() => undefined);
        const { data } = await supabase.auth.getSession();
        if (data.session) return; // still signed in → do NOT switch storage to the guest
      }
      applyIdentity(null);
      clearSearchCache();
      void wipeStage6Local(); // the in-browser net was trained on this identity's learner
      if (uid && brainSafeOnServer) {
        try {
          await forgetLocalBrain(uid);
        } catch {
          /* best effort — the mirror is under the user's own key either way */
        }
      }
    },
  };
}
