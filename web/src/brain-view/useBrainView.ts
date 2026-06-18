// Bridges AI-1's live BRAIN graph into the 3D view: real data via useBrainGraph(),
// a brain-shaped 3D layout (brainLayout.ts), and stats. Falls back to a mock graph
// when the live brain is still empty (signed-out / no memory yet) so /brain is
// never blank.
import { useMemo } from 'react';
import { useBrainGraph } from '../brain';
import type { BrainGraph, BrainStats, Positions } from './types';
import { mockGraph } from './mockGraph';
import { brainLayout } from './brainLayout';

// Render ceiling (LOD). The engine now hands us HUNDREDS OF THOUSANDS of words; we
// keep the most important ones — enough to FILL a dense, human-brain-like volume —
// rendered at 60 fps via instanced points + a single line-segments draw call (see
// BrainScene). Profile/pinned always kept; edges only between kept nodes (no
// dangling strands), and capped to the strongest so it stays a brain, not a blob.
const MAX_NODES = 30000;
const MAX_EDGES = 65000;

function capGraph(g: BrainGraph, maxNodes: number, maxEdges: number): BrainGraph {
  let nodes = g.nodes;
  let keep: Set<string> | null = null;
  if (nodes.length > maxNodes) {
    const score = (n: BrainGraph['nodes'][number]) =>
      (n.kind === 'profile' ? 1e7 : 0) + (n.pinned ? 1e6 : 0) + (n.weight ?? 0);
    nodes = [...g.nodes].sort((a, b) => score(b) - score(a)).slice(0, maxNodes);
    keep = new Set(nodes.map((n) => n.id));
  }
  let edges = keep ? g.edges.filter((e) => keep!.has(e.a) && keep!.has(e.b)) : g.edges;
  // PER-NODE degree cap: keep each node's strongest ~PER_NODE links. Stops a single
  // "super-hub" (e.g. a region hub wired to thousands of words) from spraying an
  // X-burst of lines; the result is an even web over the brain shell. Every drawn
  // strand is still REAL — we just keep the strongest per node (LOD, BRAIN.md §30.2).
  const PER_NODE = 16;
  const strongest = [...edges].sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0));
  const deg = new Map<string, number>();
  const capped: typeof edges = [];
  for (const e of strongest) {
    const da = deg.get(e.a) ?? 0;
    const db = deg.get(e.b) ?? 0;
    if (da >= PER_NODE || db >= PER_NODE) continue;
    capped.push(e);
    deg.set(e.a, da + 1);
    deg.set(e.b, db + 1);
    if (capped.length >= maxEdges) break;
  }
  edges = capped;
  return { nodes, edges, regions: g.regions };
}

function mockStats(g: BrainGraph): BrainStats {
  const by = (k: string) => g.nodes.filter((n) => n.kind === k).length;
  return {
    conversations: 0,
    facts: by('fact') + by('summary'),
    keywords: by('keyword'),
    docs: by('doc'),
    vocab: g.nodes.length,
    fullnessPct: Math.min(100, Math.round((g.nodes.length / 6000) * 100)),
    lastLearnedAt: null,
  };
}

export function useBrainView(): {
  graph: BrainGraph;
  positions: Positions;
  stats: BrainStats;
  isMock: boolean;
} {
  const { graph: live, stats: liveStats } = useBrainGraph();
  const isMock = live.nodes.length === 0;
  const base = isMock ? mockGraph : live;
  const graph = useMemo(() => capGraph(base, MAX_NODES, MAX_EDGES), [base]);
  const positions = useMemo(() => brainLayout(graph), [graph]);
  const stats = isMock ? mockStats(base) : liveStats;
  return { graph, positions, stats, isMock };
}
