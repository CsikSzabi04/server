// AI-3 (BODY) — login bridge between the AuriGPT account and the Jarvis daemon (spec 5.11).
//
// - Signed in (useAuth) + socket open → send {type:"auth", access_token} once per connection
//   and user; the DAEMON verifies it against Supabase (/auth/v1/user). No password and no
//   refresh token ever leave the browser.
// - Signed out IN THIS WINDOW while the daemon still has a user → send "logout" (daemon →
//   guest at once). A window that was never signed in never logs anyone out.
// - `prefs.changed` from the daemon → merge into Supabase profiles.prefs.jarvis:
//   getProfile → replace ONLY prefs.jarvis → saveProfile (the rest of the profile is kept).
import { useEffect, useRef, useState } from 'react';
import type { AuthApi } from '../hooks/useAuth';
import { getProfile, saveProfile } from '../lib/memStore';
import { supabase } from '../lib/supabase';
import type { JarvisLink } from './useJarvisSocket';

export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

export function useAuthBridge(auth: AuthApi, link: JarvisLink): { saveState: SaveState } {
  const { status, model, send } = link;
  const sentFor = useRef<string | null>(null);
  const hadUser = useRef(false); // this window has seen a signed-in user (→ a sign-out here is real)
  const savedSeq = useRef(0);
  const [saveState, setSaveState] = useState<SaveState>('idle');

  // a new connection must re-authenticate
  useEffect(() => {
    if (status !== 'open') sentFor.current = null;
  }, [status]);

  useEffect(() => {
    if (status !== 'open' || !auth.ready) return;
    const uid = auth.user?.id ?? null;
    if (uid) hadUser.current = true;
    if (uid) {
      if (sentFor.current === uid) return;
      sentFor.current = uid;
      void supabase?.auth.getSession().then(({ data }) => {
        const tok = data.session?.access_token;
        if (tok && data.session?.user?.id === uid) send('auth', { access_token: tok });
      });
    } else if (auth.configured && hadUser.current && model.identity.tier === 'user') {
      // only a sign-out IN THIS WINDOW logs the daemon out — a second, never-signed-in HUD
      // window (another browser, a test) must not kick the user out of their Jarvis
      hadUser.current = false;
      sentFor.current = null;
      send('logout', {});
    }
  }, [status, auth.ready, auth.user?.id, auth.configured, model.identity.tier, send]);

  useEffect(() => {
    const pc = model.prefsChanged;
    const uid = auth.user?.id;
    if (!pc || pc.seq === savedSeq.current || !uid || model.identity.userId !== uid) return;
    savedSeq.current = pc.seq;
    setSaveState('saving');
    void (async () => {
      try {
        const profile = await getProfile(uid);
        const prefs = { ...(profile.prefs ?? {}), jarvis: { ...pc.prefs, updated_at: pc.updated_at } };
        await saveProfile(uid, { prefs });
        setSaveState('saved');
      } catch {
        setSaveState('error');
      }
    })();
  }, [model.prefsChanged, model.identity.userId, auth.user?.id]);

  return { saveState };
}
