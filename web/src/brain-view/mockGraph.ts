// Fallback graph for when the live BRAIN is empty (e.g. signed-out / no memory
// yet), so /brain isn't a blank screen. Conforms to AI-1's contract types.
import type { BrainEdge, BrainGraph, BrainNode, BrainRegion } from '../brain/contracts';

const REGION_DEFS: Array<{ id: string; label: string; hue: number }> = [
  { id: 'self', label: 'You', hue: 190 },
  { id: 'work', label: 'Work / CliMarkAI', hue: 200 },
  { id: 'code', label: 'Programming', hue: 175 },
  { id: 'docs', label: 'Documents', hue: 140 },
  { id: 'lang', label: 'Languages', hue: 280 },
];

const WORDS: Record<string, string[]> = {
  work: ['climarkai', 'project', 'marketing', 'deadline', 'client', 'launch'],
  code: ['python', 'typescript', 'react', 'backend', 'api', 'ollama', 'vite'],
  docs: ['architecture.md', 'notes.txt', 'spec', 'schema', 'pipeline'],
  lang: ['hungarian', 'english', 'translate', 'grammar'],
};

function colorFor(kind: BrainNode['kind'], hue: number): string {
  if (kind === 'profile') return '#eaffff';
  if (kind === 'doc' || kind === 'summary') return '#36e0a0';
  if (kind === 'fact') return '#ffd166';
  return `hsl(${hue}, 90%, 62%)`;
}

function build(): BrainGraph {
  const nodes: BrainNode[] = [];
  const edges: BrainEdge[] = [];

  nodes.push({
    id: 'profile',
    label: 'You',
    kind: 'profile',
    weight: 14,
    freshness: 0.5,
    pinned: true,
    regionId: 'self',
    sources: [],
    color: colorFor('profile', 190),
  });

  for (const region of REGION_DEFS) {
    if (region.id === 'self') continue;
    const words = WORDS[region.id] ?? [];
    const kind: BrainNode['kind'] = region.id === 'docs' ? 'doc' : 'keyword';
    let prev = 'profile';
    words.forEach((w, i) => {
      const id = `${region.id}:${w}`;
      nodes.push({
        id,
        label: w,
        kind,
        weight: 2 + ((i * 3) % 7),
        freshness: i === 0 ? 0.9 : 0.2 + (i % 4) * 0.15,
        pinned: i === 1 && region.id === 'work',
        regionId: region.id,
        sources: [`${region.id}-source`],
        color: colorFor(kind, region.hue),
      });
      edges.push({ a: prev, b: id, strength: Math.max(0.3, 0.9 - i * 0.12), dir: 1, fresh: false });
      if (i > 1) edges.push({ a: `${region.id}:${words[0]}`, b: id, strength: 0.4, dir: 0, fresh: false });
      prev = id;
    });
    edges.push({ a: 'profile', b: `${region.id}:${words[0]}`, strength: 0.85, dir: 1, fresh: false });
  }

  edges.push({ a: 'code:python', b: 'work:project', strength: 0.6, dir: 0, fresh: false });
  edges.push({ a: 'code:react', b: 'docs:architecture.md', strength: 0.5, dir: 0, fresh: false });
  edges.push({ a: 'lang:hungarian', b: 'work:marketing', strength: 0.35, dir: 0, fresh: false });

  const regions: BrainRegion[] = REGION_DEFS.map((r) => ({
    id: r.id,
    label: r.label,
    hue: r.hue,
    nodeIds: nodes.filter((n) => n.regionId === r.id).map((n) => n.id),
  }));

  return { nodes, edges, regions };
}

export const mockGraph: BrainGraph = build();
