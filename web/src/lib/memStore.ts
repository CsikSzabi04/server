// Storage for the BRAIN: Supabase when signed in (syncs across devices, survives
// cache clears), localStorage fallback for anonymous users. All functions accept
// userId|null and degrade gracefully if Supabase/tables aren't available.
import { supabase } from './supabase';
import type { Memory, Profile } from './memory';

const LS_PROFILE = 'auri.profile';
const LS_MEM = 'auri.memories';

function lsGet<T>(key: string, def: T): T {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : def;
  } catch {
    return def;
  }
}
function lsSet(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked */
  }
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
  return lsGet<Profile>(LS_PROFILE, {});
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
    lsSet(LS_PROFILE, merged);
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
      .limit(500);
    if (error || !data) return [];
    return data.map(mapMem);
  }
  return lsGet<Memory[]>(LS_MEM, []);
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
  const all = lsGet<Memory[]>(LS_MEM, []);
  const m: Memory = { ...mem, id: crypto.randomUUID(), created_at: new Date().toISOString() };
  all.unshift(m);
  lsSet(LS_MEM, all.slice(0, 500));
  return m;
}

export async function bumpWeight(userId: string | null, id: string, weight: number): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').update({ weight }).eq('id', id);
    return;
  }
  const all = lsGet<Memory[]>(LS_MEM, []);
  const i = all.findIndex((m) => m.id === id);
  if (i >= 0) {
    all[i].weight = weight;
    lsSet(LS_MEM, all);
  }
}

export async function deleteMemory(userId: string | null, id: string): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').delete().eq('id', id);
    return;
  }
  lsSet(
    LS_MEM,
    lsGet<Memory[]>(LS_MEM, []).filter((m) => m.id !== id),
  );
}

export async function setMemoryPinned(userId: string | null, id: string, pinned: boolean): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').update({ pinned }).eq('id', id);
    return;
  }
  const all = lsGet<Memory[]>(LS_MEM, []);
  const i = all.findIndex((m) => m.id === id);
  if (i >= 0) {
    all[i].pinned = pinned;
    lsSet(LS_MEM, all);
  }
}

export async function clearAll(userId: string | null): Promise<void> {
  if (userId && supabase) {
    await supabase.from('memories').delete().eq('user_id', userId);
    await supabase.from('profiles').delete().eq('user_id', userId);
    return;
  }
  lsSet(LS_MEM, []);
  try {
    localStorage.removeItem(LS_PROFILE);
  } catch {
    /* ignore */
  }
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
