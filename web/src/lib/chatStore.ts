// Conversation persistence. Unified store: Supabase when signed in (syncs,
// survives cache clears), localStorage fallback for guests — so chat history
// works for everyone. Every function degrades gracefully on error.
import { supabase } from './supabase';
import type { Role } from './api';

export interface StoredMessage {
  role: Role;
  content: string;
}

export interface ConversationMeta {
  id: string;
  title: string;
  updatedAt: string;
  pinned: boolean;
  keywords?: string[];
}

interface LocalConversation extends ConversationMeta {
  createdAt: string;
  messages: StoredMessage[];
}

const LS_KEY = 'auri.conversations';
const lsGet = (): LocalConversation[] => {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]') as LocalConversation[];
  } catch {
    return [];
  }
};
const lsSet = (v: LocalConversation[]) => {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(v));
  } catch {
    /* storage blocked */
  }
};

const titleOf = (s: string) => s.trim().replace(/\s+/g, ' ').slice(0, 60) || 'Új beszélgetés';

export async function listConversations(userId: string | null): Promise<ConversationMeta[]> {
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('conversations')
      .select('id, title, updated_at, keywords, pinned')
      .eq('user_id', userId)
      .order('pinned', { ascending: false })
      .order('updated_at', { ascending: false });
    if (error || !data) return [];
    return data.map((d: any) => ({
      id: d.id,
      title: d.title ?? 'Beszélgetés',
      updatedAt: d.updated_at,
      pinned: !!d.pinned,
      keywords: d.keywords ?? [],
    }));
  }
  return lsGet()
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || (a.updatedAt < b.updatedAt ? 1 : -1))
    .map(({ id, title, updatedAt, pinned, keywords }) => ({ id, title, updatedAt, pinned, keywords }));
}

export async function loadConversation(userId: string | null, id: string): Promise<StoredMessage[]> {
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('messages')
      .select('role, content')
      .eq('conversation_id', id)
      .order('created_at', { ascending: true });
    if (error || !data) return [];
    return data as StoredMessage[];
  }
  return lsGet().find((c) => c.id === id)?.messages ?? [];
}

export async function createConversation(userId: string | null, firstMessage: string): Promise<string | null> {
  const title = titleOf(firstMessage);
  if (userId && supabase) {
    const { data, error } = await supabase
      .from('conversations')
      .insert({ user_id: userId, title })
      .select('id')
      .single();
    if (error || !data) {
      console.warn('[chatStore] createConversation:', error?.message);
      return null;
    }
    return data.id as string;
  }
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  const all = lsGet();
  all.unshift({ id, title, pinned: false, createdAt: now, updatedAt: now, messages: [] });
  lsSet(all);
  return id;
}

export async function saveMessage(
  userId: string | null,
  conversationId: string,
  role: Role,
  content: string,
): Promise<void> {
  if (!content.trim()) return;
  if (userId && supabase) {
    await supabase.from('messages').insert({ conversation_id: conversationId, user_id: userId, role, content });
    void supabase
      .from('conversations')
      .update({ updated_at: new Date().toISOString() })
      .eq('id', conversationId);
    return;
  }
  const all = lsGet();
  const c = all.find((x) => x.id === conversationId);
  if (c) {
    c.messages.push({ role, content });
    c.updatedAt = new Date().toISOString();
    lsSet(all);
  }
}

export async function renameConversation(userId: string | null, id: string, title: string): Promise<void> {
  const t = titleOf(title);
  if (userId && supabase) {
    await supabase.from('conversations').update({ title: t }).eq('id', id);
    return;
  }
  const all = lsGet();
  const c = all.find((x) => x.id === id);
  if (c) {
    c.title = t;
    lsSet(all);
  }
}

export async function deleteConversation(userId: string | null, id: string): Promise<void> {
  if (userId && supabase) {
    await supabase.from('conversations').delete().eq('id', id);
    return;
  }
  lsSet(lsGet().filter((x) => x.id !== id));
}

export async function setPinned(userId: string | null, id: string, pinned: boolean): Promise<void> {
  if (userId && supabase) {
    await supabase.from('conversations').update({ pinned }).eq('id', id);
    return;
  }
  const all = lsGet();
  const c = all.find((x) => x.id === id);
  if (c) {
    c.pinned = pinned;
    lsSet(all);
  }
}
