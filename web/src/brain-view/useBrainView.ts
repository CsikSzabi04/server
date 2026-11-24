// Bridges AI-1's live BRAIN graph into the 3D view: real data via useBrainGraph(),
// an anatomical layout (brainLayout.ts / anatomy.ts), and stats. Falls back to a
// mock graph when the live brain is still empty so /brain is never blank.
import { useMemo, useRef } from 'react';
import { useBrainGraph } from '../brain';
import type { BrainGraph, BrainStats, Positions } from './types';
import { mockGraph } from './mockGraph';
import { brainLayout, type BrainLayout } from './brainLayout';

// Render ceiling (LOD). REAL knowledge (anything not machine-generated) always wins
// a slot first; synthetic self-built tokens ("bulk:*") only fill what is left, and
// are capped so they stay a faint substrate instead of drowning the real brain.
const MAX_NODES = 30000;
const MAX_PROTO = 14000;
const MAX_EDGES = 65000;
const PER_NODE = 16;

const isProto = (n: BrainGraph['nodes'][number]): boolean => (n.sources?.[0] ?? '').startsWith('bulk:');

function capGraph(g: BrainGraph): BrainGraph {
  const score = (n: BrainGraph['nodes'][number]) =>
    (n.kind === 'profile' ? 1e7 : 0) + (n.pinned ? 1e6 : 0) + (isProto(n) ? 0 : 1e4) + (n.weight ?? 0);
  const sorted = [...g.nodes].sort((a, b) => score(b) - score(a));
  const nodes: BrainGraph['nodes'] = [];
  let proto = 0;
  for (const n of sorted) {
    if (nodes.length >= MAX_NODES) break;
    if (isProto(n)) {
      if (proto >= MAX_PROTO) continue;
      proto++;
    }
    nodes.push(n);
  }
  const keep = new Set(nodes.map((n) => n.id));
  // PER-NODE degree cap: keep each node's strongest links, so a region hub wired to
  // thousands of words doesn't spray an X-burst. Every kept strand is REAL.
  const strongest = g.edges
    .filter((e) => keep.has(e.a) && keep.has(e.b))
    .sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0));
  const deg = new Map<string, number>();
  const edges: typeof g.edges = [];
  for (const e of strongest) {
    const da = deg.get(e.a) ?? 0;
    const db = deg.get(e.b) ?? 0;
    if (da >= PER_NODE || db >= PER_NODE) continue;
    edges.push(e);
    deg.set(e.a, da + 1);
    deg.set(e.b, db + 1);
    if (edges.length >= MAX_EDGES) break;
  }
  return { nodes, edges, regions: g.regions };
}

/** Cheap structural fingerprint: sizes + a sparse sample of ids and weights. */
function signature(g: BrainGraph): string {
  const n = g.nodes.length;
  let s = `${n}|${g.edges.length}`;
  const step = Math.max(1, Math.floor(n / 48));
  for (let i = 0; i < n; i += step) s += `|${g.nodes[i].id}:${Math.round(g.nodes[i].weight ?? 0)}`;
  return s;
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
  layout: BrainLayout;
  positions: Positions;
  stats: BrainStats;
  isMock: boolean;
} {
  const { graph: live, stats: liveStats } = useBrainGraph();
  const isMock = live.nodes.length === 0;
  const base = isMock ? mockGraph : live;
  // The engine re-emits often (e.g. every Stage-6 training epoch) with a graph that
  // is structurally unchanged. Reuse the previous view graph then, so the 3D brain
  // isn't rebuilt (and its impulses reset) for nothing.
  const last = useRef<{ sig: string; graph: BrainGraph } | null>(null);
  const graph = useMemo(() => {
    const sig = signature(base);
    if (last.current?.sig === sig) return last.current.graph;
    const g = capGraph(base);
    last.current = { sig, graph: g };
    return g;
  }, [base]);
  const layout = useMemo(() => brainLayout(graph), [graph]);
  const stats = isMock ? mockStats(base) : liveStats;
  return { graph, layout, positions: layout.positions, stats, isMock };
}
