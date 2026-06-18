// Minimal Supabase auth hook: tracks the signed-in user and exposes
// sign-in / sign-up / sign-out. Email+password (works with Supabase's default
// email provider). Returns an error message string (or null on success).
import { useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

export interface AuthApi {
  user: User | null;
  ready: boolean;
  configured: boolean;
  signIn: (email: string, password: string) => Promise<string | null>;
  signUp: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthApi {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(!isSupabaseConfigured());

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null);
      setReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
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
    async signUp(email, password) {
      if (!supabase) return 'Supabase is not configured.';
      const { error } = await supabase.auth.signUp({ email, password });
      return error?.message ?? null;
    },
    async signOut() {
      await supabase?.auth.signOut();
    },
  };
}
