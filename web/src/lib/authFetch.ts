// authFetch.ts — lets our own serverless proxy (/api/*) recognise a signed-in user
// (higher rate limits; AURI_REQUIRE_LOGIN support — SECURITY.md §8, api/_guard.ts).
//
// SECURITY: the Supabase access token is attached ONLY to same-origin, relative
// URLs ('/api/...'). It is never sent to a direct backend URL or a third-party
// provider (BYO keys talk to providers without it).
import { supabase } from './supabase';

/** `{ authorization: 'Bearer <token>' }` for a same-origin URL when signed in, else {}. */
export async function apiAuthHeader(url: string): Promise<Record<string, string>> {
  if (!supabase || !url.startsWith('/') || url.startsWith('//')) return {};
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}
