// React glue for the BRAIN: loads profile + memories, injects context, learns
// from each turn, ingests uploaded documents, and exposes management ops.
import { useCallback, useEffect, useRef, useState } from 'react';
import * as store from '../lib/memStore';
import type { MemoryExport } from '../lib/memStore';
import {
  analyzeTurn,
  buildSystemMessage,
  extractKeywords,
  textSimilar,
  type Memory,
  type Profile,
} from '../lib/memory';
import { chunkText, readDocument, summarizeWithModel } from '../lib/files';

export interface MemoryApi {
  profile: Profile;
  memories: Memory[];
  systemMessage: (query: string) => string;
  ingest: (userText: string, assistantText: string) => Promise<boolean>;
  addDocument: (file: File) => Promise<void>;
  removeDoc: (source: string) => Promise<void>;
  updateProfile: (patch: Partial<Profile>) => Promise<void>;
  removeMemory: (id: string) => Promise<void>;
  pinMemory: (id: string, pinned: boolean) => Promise<void>;
  clearAll: () => Promise<void>;
  exportData: () => Promise<MemoryExport>;
  importData: (data: MemoryExport) => Promise<void>;
  optimize: () => Promise<{ removed: number }>;
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

  // Add or increment a keyword memory (shared by ingest + addDocument).
  const bumpKeyword = useCallback(
    async (kw: string) => {
      const existing = memRef.current.find((m) => m.kind === 'keyword' && m.content === kw);
      if (existing?.id) {
        existing.weight += 1;
        await store.bumpWeight(userId, existing.id, existing.weight);
      } else {
        const m = await store.addMemory(userId, { kind: 'keyword', content: kw, weight: 1 });
        if (m) memRef.current = [m, ...memRef.current];
      }
    },
    [userId],
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

      for (const kw of a.keywords) await bumpKeyword(kw);

      for (const fact of a.facts) {
        const dup = memRef.current.find(
          (m) => (m.kind === 'fact' || m.kind === 'summary') && textSimilar(m.content, fact),
        );
        if (dup?.id) {
          // near-duplicate fact → reinforce it instead of storing a copy
          dup.weight += 1;
          await store.bumpWeight(userId, dup.id, dup.weight);
        } else {
          const m = await store.addMemory(userId, { kind: 'fact', content: fact, weight: 3, source: 'chat' });
          if (m) memRef.current = [m, ...memRef.current];
        }
      }

      setMemories([...memRef.current]);
      return learnedName;
    },
    [userId, bumpKeyword],
  );

  const addDocument = useCallback(
    async (file: File) => {
      const text = await readDocument(file); // throws a friendly error on bad file
      const chunks = chunkText(text);
      if (!chunks.length) throw new Error('Empty or unreadable file.');

      for (const ch of chunks) {
        const m = await store.addMemory(userId, { kind: 'doc', content: ch, weight: 4, source: file.name });
        if (m) memRef.current = [m, ...memRef.current];
      }
      for (const kw of extractKeywords(text, 12)) await bumpKeyword(kw);
      setMemories([...memRef.current]);

      // Best-effort: let the model write a short summary (skipped in mock mode).
      const summary = await summarizeWithModel(file.name, text);
      if (summary) {
        const m = await store.addMemory(userId, {
          kind: 'summary',
          content: `[${file.name}] ${summary}`,
          weight: 5,
          source: file.name,
        });
        if (m) {
          memRef.current = [m, ...memRef.current];
          setMemories([...memRef.current]);
        }
      }
    },
    [userId, bumpKeyword],
  );

  const removeDoc = useCallback(
    async (source: string) => {
      const toRemove = memRef.current.filter((m) => m.kind === 'doc' && (m.source || 'untitled') === source);
      for (const m of toRemove) if (m.id) await store.deleteMemory(userId, m.id);
      memRef.current = memRef.current.filter((m) => !(m.kind === 'doc' && (m.source || 'untitled') === source));
      setMemories([...memRef.current]);
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

  // Optimize: merge near-duplicate facts/summaries (sum their weights) and decay
  // + prune faded keyword weights by age. Returns how many memories were removed.
  const optimize = useCallback(async (): Promise<{ removed: number }> => {
    let removed = 0;

    // 1) merge near-duplicate facts / summaries
    const factual = memRef.current.filter((m) => m.kind === 'fact' || m.kind === 'summary');
    const kept: Memory[] = [];
    for (const f of factual) {
      const dup = kept.find((k) => textSimilar(k.content, f.content));
      if (dup?.id && f.id) {
        dup.weight += f.weight;
        await store.bumpWeight(userId, dup.id, dup.weight);
        await store.deleteMemory(userId, f.id);
        memRef.current = memRef.current.filter((m) => m.id !== f.id);
        removed++;
      } else {
        kept.push(f);
      }
    }

    // 2) decay keyword weights by age; prune the faded ones
    for (const k of memRef.current.filter((m) => m.kind === 'keyword')) {
      const ageDays = k.created_at ? (Date.now() - new Date(k.created_at).getTime()) / 86_400_000 : 0;
      const decayed = Math.max(0, (k.weight ?? 1) - Math.floor(ageDays / 30));
      if (decayed <= 0 && k.id) {
        await store.deleteMemory(userId, k.id);
        memRef.current = memRef.current.filter((m) => m.id !== k.id);
        removed++;
      } else if (decayed !== k.weight && k.id) {
        k.weight = decayed;
        await store.bumpWeight(userId, k.id, decayed);
      }
    }

    setMemories([...memRef.current]);
    return { removed };
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
    addDocument,
    removeDoc,
    updateProfile,
    removeMemory,
    pinMemory,
    clearAll,
    exportData,
    importData,
    optimize,
  };
}
