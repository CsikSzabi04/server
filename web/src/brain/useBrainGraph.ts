// useBrainGraph — React hook: builds the live BrainGraph + BrainStats from the
// existing memory (read-only). Works with empty memory (returns an empty graph),
// so AI-2's 3D view can render before there is any data.
import { useEffect, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useMemory } from '../hooks/useMemory';
import { buildBrainGraph } from './graph';
import { initLearner, useBrainVersion, ensureHydrated } from './useBrainLearning';
import type { BrainGraphResult } from './contracts';

export function useBrainGraph(): BrainGraphResult {
  const auth = useAuth();
  const userId = auth.user?.id ?? null;
  const memory = useMemory(userId);
  const version = useBrainVersion(); // re-render when the shared brain hydrates/grows

  // Load the persisted brain (IndexedDB/Supabase) even if /brain is opened alone.
  useEffect(() => {
    ensureHydrated(userId);
  }, [userId]);

  // Cheap conversation count (guests): read chatStore's localStorage key directly.
  const conversations = useMemo(() => {
    try {
      return (JSON.parse(localStorage.getItem('auri.conversations') || '[]') as unknown[]).length;
    } catch {
      return 0;
    }
  }, []);

  // The seeded/learned language layer (alphabet + vocab + Markov links) — the SHARED
  // singleton brain. Rebuild when memory changes OR the brain hydrates/grows (version).
  const { graph, stats } = useMemo(
    () => buildBrainGraph(memory.profile, memory.memories, conversations, initLearner()),
    [memory.profile, memory.memories, conversations, version],
  );

  return { graph, stats, loading: false };
}
