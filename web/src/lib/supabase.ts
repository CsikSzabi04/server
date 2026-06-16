// Supabase client (browser). Uses the PUBLISHABLE/anon key — safe to ship to
// the client; access is guarded by Row Level Security on the database side.
// If the env vars aren't set, the app still runs (just without login/saving).
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = (import.meta.env.VITE_SUPABASE_URL as string | undefined)?.trim() || '';
const anon = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined)?.trim() || '';

export function isSupabaseConfigured(): boolean {
  return !!url && !!anon;
}

export const supabase: SupabaseClient | null = isSupabaseConfigured()
  ? createClient(url, anon, { auth: { persistSession: true, autoRefreshToken: true } })
  : null;
