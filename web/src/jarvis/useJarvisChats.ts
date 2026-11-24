// AI-3 (BODY) — Jarvis conversations in the AuriGPT ARCHIVE (the same `chatStore` the main app
// uses, import-only). The live Jarvis chat (voice transcripts, typed commands, replies) is saved
// message by message into the signed-in user's account; NEW CHAT starts a new conversation;
// opening an archived chat loads it into the panel and later turns continue it.
//
// PRIVACY: guests save NOTHING (no localStorage history either) — a guest session never leaves
// personal traces on the machine (spec 5.11: the guest "memory" lives in RAM only).
import { useCallback, useEffect, useRef, useState } from 'react';
import type { AuthApi } from '../hooks/useAuth';
import {
  type ConversationMeta,
  createConversation,
  deleteConversation,
  listConversations,
  loadConversation,
  renameConversation,
  saveMessage,
  setPinned,
} from '../lib/chatStore';
import type { UIMessage } from '../types';
import type { JarvisLink } from './useJarvisSocket';

export interface JarvisChats {
  conversations: ConversationMeta[];
  currentId: string | null;
  enabled: boolean;
  refresh: () => void;
  newChat: () => void;
  open: (id: string) => Promise<void>;
  rename: (id: string, title: string) => void;
  remove: (id: string) => void;
  pin: (id: string, pinned: boolean) => void;
}

export function useJarvisChats(auth: AuthApi, link: JarvisLink): JarvisChats {
  const uid = auth.user?.id ?? null;
  // only when the daemon ALSO knows this user (never mix a guest daemon with an account)
  const enabled = !!uid && link.model.identity.tier === 'user' && link.model.identity.userId === uid;
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const convRef = useRef<string | null>(null);
  const saved = useRef<Set<string>>(new Set());
  const queue = useRef<Promise<void>>(Promise.resolve());

  const refresh = useCallback(() => {
    if (!uid) {
      setConversations([]);
      return;
    }
    void listConversations(uid).then(setConversations);
  }, [uid]);

  // account switch / logout → forget the current conversation
  useEffect(() => {
    convRef.current = null;
    setCurrentId(null);
    saved.current = new Set(link.model.chat.map((m) => m.id)); // never save what was said before
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid, enabled]);

  // save every finished message of the live chat, in order
  useEffect(() => {
    if (!enabled || !uid) return;
    for (const m of link.model.chat) {
      if (m.streaming || saved.current.has(m.id) || !m.content.trim()) continue;
      saved.current.add(m.id);
      queue.current = queue.current
        .then(async () => {
          if (!convRef.current) {
            const id = await createConversation(uid, m.content);
            if (!id) return;
            convRef.current = id;
            setCurrentId(id);
          }
          await saveMessage(uid, convRef.current, m.role, m.content);
          refresh();
        })
        .catch(() => {
          /* best effort — the live HUD never blocks on storage */
        });
    }
  }, [link.model.chat, enabled, uid, refresh]);

  const newChat = useCallback(() => {
    convRef.current = null;
    setCurrentId(null);
    link.local({ type: 'local.newChat' });
  }, [link]);

  const open = useCallback(
    async (id: string) => {
      if (!uid) return;
      const msgs = await loadConversation(uid, id);
      const ui: UIMessage[] = msgs
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m, i) => ({ id: `hist-${id}-${i}`, role: m.role, content: m.content }));
      ui.forEach((m) => saved.current.add(m.id)); // already stored
      convRef.current = id;
      setCurrentId(id);
      link.local({ type: 'local.loadChat', messages: ui });
    },
    [uid, link],
  );

  const rename = useCallback(
    (id: string, title: string) => {
      if (uid) void renameConversation(uid, id, title).then(refresh);
    },
    [uid, refresh],
  );

  const remove = useCallback(
    (id: string) => {
      if (!uid) return;
      if (convRef.current === id) newChat();
      void deleteConversation(uid, id).then(refresh);
    },
    [uid, refresh, newChat],
  );

  const pin = useCallback(
    (id: string, pinned: boolean) => {
      if (uid) void setPinned(uid, id, pinned).then(refresh);
    },
    [uid, refresh],
  );

  return { conversations, currentId, enabled, refresh, newChat, open, rename, remove, pin };
}
