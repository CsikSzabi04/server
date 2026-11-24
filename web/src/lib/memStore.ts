// Storage for the personal memory (profile + memories).
//
// PRIVACY RULE: personal data lives ONLY in the signed-in user's own account
// (Supabase, Row Level Security → only that user can read it). A logged-out (guest)
// session gets NO persistent personal memory: its profile + memories live only in
// this tab's RAM and vanish on reload / login / logout. So a logged-out screen can
// never show a signed-in user's — or a previous guest's — personal data.
//
// (Older builds kept guest data in localStorage under 'auri.profile' / 'auri.memories'.
//  Those keys are intentionally NEVER read anymore.)
// All functions accept userId|null and degrade gracefully if Supabase is unavailable.
import { supabase } from './supabase';
import type { Memory, Profile } from './memory';

// Guest (logged-out) memory: RAM only, this tab only.
let guestProfile: Profile = {};
let guestMemories: Memory[] = [];
const GUEST_MEM_CAP = 5000;

/** Forget the guest's RAM memory — called on every login / logout (useAuth), so facts
 *  typed as a guest never show up for whoever uses the tab next (or in the account). */
export function resetGuestMemory(): void {
  guestProfile = {};
  guestMemories = [];
}

export async function getProfile(userId: string | null): Promise<Profile> {
  if (userId && supabase) {
    const { data, error } = await supabase.from('profiles').select('*').eq('user_id', userId).maybeSingle();
    if (error || !data) return {};
    return {
      name: data.name ?? undefined,
      nickname: data.nickname ?? undefined,
      language: data.language ?? undefined,
      tone: data.tone ?? undefined,
      about: data.about ?? undefined,
      interests: data.interests ?? [],
      prefs: data.prefs ?? {},
    };
  }
  return { ...guestProfile };
}

export async function saveProfile(userId: string | null, patch: Partial<Profile>): Promise<Profile> {
  const current = await getProfile(userId);
  const merged: Profile = { ...current, ...patch };
  if (userId && supabase) {
    await supabase.from('profiles').upsert({
      user_id: userId,
      name: merged.name ?? null,
      nickname: merged.nickname ?? null,
      language: merged.language ?? null,
      tone: merged.tone ?? null,
      about: merged.about ?? null,
      interests: merged.interests ?? [],
      prefs: merged.prefs ?? {},
      updated_at: new Date().toISOString(),
    });
  } else {
    guestProfile = merged;
  }
  return merged;
}

function mapMem(d: Record<string, any>): Memory {
  return {
    id: d.id,
    kind: d.kind,
    content: d.content,
    weight: d.weight,
    pinned: d.pinned,
    source: d.source ?? undefined,
    created_at: d.created_at,
  };
}

export async function listMemories(userId: string | null): Promise<Memory[]> {
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('memories')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(10000);
    if (error || !data) return [];
    return data.map(mapMem);
  }
  return [...guestMemories];
}

export async function addMemory(userId: string | null, mem: Memory): Promise<Memory | null> {
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('memories')
      .insert({
        user_id: userId,
        kind: mem.kind,
        content: mem.content,
        weight: mem.weight,
        pinned: mem.pinned ?? false,
        source: mem.source ?? null,
      })
      .select('*')
      .single();
    if (error || !data) return null;
    return mapMem(data);
  }
  const m: Memory = { ...mem, id: crypto.randomUUID(), created_at: new Date().toISOString() };
  guestMemories = [m, ...guestMemories].slice(0, GUEST_MEM_CAP);
  return m;
}

export async function bumpWeight(userId: string | null, id: string, weight: number): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').update({ weight }).eq('id', id);
    return;
  }
  const g = guestMemories.find((m) => m.id === id);
  if (g) g.weight = weight;
}

export async function deleteMemory(userId: string | null, id: string): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').delete().eq('id', id);
    return;
  }
  guestMemories = guestMemories.filter((m) => m.id !== id);
}

export async function setMemoryPinned(userId: string | null, id: string, pinned: boolean): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').update({ pinned }).eq('id', id);
    return;
  }
  const g = guestMemories.find((m) => m.id === id);
  if (g) g.pinned = pinned;
}

export async function clearAll(userId: string | null): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').delete().eq('user_id', userId);
    await supabase.from('profiles').delete().eq('user_id', userId);
    return;
  }
  guestMemories = [];
  guestProfile = {};
}

export interface MemoryExport {
  profile: Profile;
  memories: Memory[];
}

export async function exportAll(userId: string | null): Promise<MemoryExport> {
  const [profile, memories] = await Promise.all([getProfile(userId), listMemories(userId)]);
  return { profile, memories };
}

export async function importAll(userId: string | null, data: MemoryExport): Promise<void> {
  if (data.profile) await saveProfile(userId, data.profile);
  if (Array.isArray(data.memories)) {
    for (const m of data.memories) {
      await addMemory(userId, {
        kind: m.kind ?? 'fact',
        content: m.content,
        weight: m.weight ?? 1,
        pinned: m.pinned ?? false,
        source: m.source,
      });
    }
  }
}
