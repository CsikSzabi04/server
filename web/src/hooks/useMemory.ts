// React glue for the BRAIN: loads profile + memories, injects context, learns
// from each turn, and exposes management ops for the Memory view.
import { useCallback, useEffect, useRef, useState } from 'react';
import * as store from '../lib/memStore';
import type { MemoryExport } from '../lib/memStore';
import { analyzeTurn, buildSystemMessage, type Memory, type Profile } from '../lib/memory';

export interface MemoryApi {
  profile: Profile;
  memories: Memory[];
  systemMessage: (query: string) => string;
  ingest: (userText: string, assistantText: string) => Promise<boolean>;
  updateProfile: (patch: Partial<Profile>) => Promise<void>;
  removeMemory: (id: string) => Promise<void>;
  pinMemory: (id: string, pinned: boolean) => Promise<void>;
  clearAll: () => Promise<void>;
  exportData: () => Promise<MemoryExport>;
  importData: (data: MemoryExport) => Promise<void>;
}

export function useMemory(userId: string | null): MemoryApi {
  const [profile, setProfile] = useState<Profile>({});
  const [memories, setMemories] = useState<Memory[]>([]);
  const profileRef = useRef<Profile>({});
  const memRef = useRef<Memory[]>([]);

  const reload = useCallback(async () => {
    const [p, m] = await Promise.all([store.getProfile(userId), store.listMemories(userId)]);
    profileRef.current = p;
    memRef.current = m;
    setProfile(p);
    setMemories(m);
  }, [userId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [p, m] = await Promise.all([store.getProfile(userId), store.listMemories(userId)]);
      if (cancelled) return;
      profileRef.current = p;
      memRef.current = m;
      setProfile(p);
      setMemories(m);
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const systemMessage = useCallback(
    (query: string) => buildSystemMessage(profileRef.current, memRef.current, query),
    [],
  );

  const ingest = useCallback(
    async (userText: string, assistantText: string): Promise<boolean> => {
      const a = analyzeTurn(userText, assistantText);
      let learnedName = false;

      const patch: Partial<Profile> = {};
      if (a.name && a.name !== profileRef.current.name) {
        patch.name = a.name;
        learnedName = true;
      }
      if (a.language && !profileRef.current.language) patch.language = a.language;
      if (Object.keys(patch).length) {
        const np = await store.saveProfile(userId, patch);
        profileRef.current = np;
        setProfile(np);
      }

      for (const kw of a.keywords) {
        const existing = memRef.current.find((m) => m.kind === 'keyword' && m.content === kw);
        if (existing?.id) {
          existing.weight += 1;
          await store.bumpWeight(userId, existing.id, existing.weight);
        } else {
          const m = await store.addMemory(userId, { kind: 'keyword', content: kw, weight: 1 });
          if (m) memRef.current = [m, ...memRef.current];
        }
      }

      for (const fact of a.facts) {
        if (!memRef.current.some((m) => m.kind === 'fact' && m.content === fact)) {
          const m = await store.addMemory(userId, { kind: 'fact', content: fact, weight: 2, source: 'chat' });
          if (m) memRef.current = [m, ...memRef.current];
        }
      }

      setMemories([...memRef.current]);
      return learnedName;
    },
    [userId],
  );

  const updateProfile = useCallback(
    async (patch: Partial<Profile>) => {
      const np = await store.saveProfile(userId, patch);
      profileRef.current = np;
      setProfile(np);
    },
    [userId],
  );

  const removeMemory = useCallback(
    async (id: string) => {
      await store.deleteMemory(userId, id);
      memRef.current = memRef.current.filter((m) => m.id !== id);
      setMemories([...memRef.current]);
    },
    [userId],
  );

  const pinMemory = useCallback(
    async (id: string, pinned: boolean) => {
      await store.setMemoryPinned(userId, id, pinned);
      const m = memRef.current.find((x) => x.id === id);
      if (m) {
        m.pinned = pinned;
        setMemories([...memRef.current]);
      }
    },
    [userId],
  );

  const clearAll = useCallback(async () => {
    await store.clearAll(userId);
    profileRef.current = {};
    memRef.current = [];
    setProfile({});
    setMemories([]);
  }, [userId]);

  const exportData = useCallback(() => store.exportAll(userId), [userId]);
  const importData = useCallback(
    async (data: MemoryExport) => {
      await store.importAll(userId, data);
      await reload();
    },
    [userId, reload],
  );

  return {
    profile,
    memories,
    systemMessage,
    ingest,
    updateProfile,
    removeMemory,
    pinMemory,
    clearAll,
    exportData,
    importData,
  };
}
