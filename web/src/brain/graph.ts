// graph.ts — pure builder: turns the BRAIN (innate base layer + personal memory)
// into a `BrainGraph` (nodes / edges / regions) for the 3D view, plus `BrainStats`.
//
// The brain has FOUR innate, always-present regions (like cortical areas):
//   Letters    — the alphabet (characters)
//   Language   — learned vocabulary + word→word (Markov) associations
//   Answering  — composing replies from what it learned
//   Reasoning  — deciding which route an answer takes (pulls from all + personal)
// The personal memory (profile, facts, keywords, docs) layers ON TOP as dynamic
// clusters and connects into Reasoning. No React, no I/O — just data → data.
import { extractKeywords, type Memory, type Profile } from '../lib/memory';
import type { BrainLearner } from './learn';
import { PROGRAMMING_SNIPPETS } from './seed/programmingCurated';
import { TECHS, TECH_LABEL } from './seed/sources';
import { getWebDocs } from './webStore';
import type { BrainEdge, BrainGraph, BrainNode, BrainRegion, BrainStats } from './contracts';

const MAX_MEM_NODES = 20000;
const MAX_LEX_NODES = 40000; // emit up to ~26k word-nodes so the 3D brain fills densely
const MAX_LETTERS = 30000;
const MAX_EDGES = 500000 // few, dim threads so they don't drown the brain SILHOUETTE
const FULLNESS_CAP = 20000; // matches the BRAIN-card capacity

// The four innate regions, with stable hues + fixed 3D seeds (AI-2 uses centroid).
const INNATE: { id: string; label: string; hue: number; centroid: [number, number, number] }[] = [
  { id: 'region:letters', label: 'Letters', hue: 200, centroid: [-6.5, 3.5, 0.5] },
  { id: 'region:language', label: 'Language', hue: 150, centroid: [-2, -1.5, 4.5] },
  { id: 'region:answering', label: 'Answering', hue: 45, centroid: [5, -0.5, -0.5] },
  { id: 'region:reasoning', label: 'Reasoning', hue: 280, centroid: [0.5, 4.5, -4] },
];

function freshnessOf(iso?: string): number {
  if (!iso) return 0.35;
  const days = (Date.now() - new Date(iso).getTime()) / 86_400_000;
  if (!Number.isFinite(days) || days < 0) return 0.5;
  return Math.max(0, Math.exp(-days / 21)); // ~3-week half-life
}
const hsl = (h: number, s = 70, l = 60): string => `hsl(${Math.round(((h % 360) + 360) % 360)} ${s}% ${l}%)`;
const clamp01 = (n: number): number => Math.max(0, Math.min(1, n));

export function buildBrainGraph(
  profile: Profile,
  memories: Memory[],
  conversations = 0,
  learner?: BrainLearner | null,
): { graph: BrainGraph; stats: BrainStats } {
  const nodes: BrainNode[] = [];
  const idByMemory = new Map<Memory, string>();
  const keywordNodeId = new Map<string, string>(); // text → node id (personal keyword OR lex)
  const baseIds = new Set<string>(); // node ids that belong to the innate base
  const fixedRegion = new Map<string, string>(); // base node id → fixed region id

  // ── innate region hubs (always present) ────────────────────────────────────
  for (const r of INNATE) {
    nodes.push({
      id: r.id,
      label: r.label,
      kind: 'keyword',
      weight: 12,
      freshness: 1,
      pinned: true,
      regionId: r.id,
      sources: ['innate'],
      color: hsl(r.hue, 78, 66),
    });
    baseIds.add(r.id);
    fixedRegion.set(r.id, r.id);
  }

  // ── personal "self" node ───────────────────────────────────────────────────
  const hasProfile = Boolean(profile.name || profile.about || (profile.interests?.length ?? 0) > 0);
  if (hasProfile) {
    nodes.push({
      id: 'profile',
      label: profile.name || 'You',
      kind: 'profile',
      weight: 14,
      freshness: 1,
      pinned: true,
      regionId: 'region:self',
      sources: ['profile'],
      color: hsl(190, 80, 68),
    });
  }

  // ── personal memory nodes ──────────────────────────────────────────────────
  const used = [...memories]
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || (b.weight ?? 1) - (a.weight ?? 1))
    .slice(0, MAX_MEM_NODES);
  used.forEach((m, i) => {
    const id = m.id ?? `${m.kind}_${i}`;
    idByMemory.set(m, id);
    if (m.kind === 'keyword') keywordNodeId.set(m.content.toLowerCase(), id);
    nodes.push({
      id,
      label: m.kind === 'keyword' ? m.content : m.content.length > 40 ? `${m.content.slice(0, 40)}…` : m.content,
      kind: m.kind,
      weight: m.weight ?? 1,
      freshness: freshnessOf(m.created_at),
      pinned: !!m.pinned,
      regionId: '',
      sources: [m.source ?? 'chat'],
      color: hsl(210),
    });
  });

  // ── innate Letters: top characters ─────────────────────────────────────────
  if (learner) {
    const topChars = [...learner.charFreq.entries()]
      .filter(([c]) => /[a-z0-9]/.test(c))
      .sort((a, b) => b[1] - a[1])
      .slice(0, MAX_LETTERS);
    for (const [ch, cnt] of topChars) {
      const id = `ltr_${ch}`;
      baseIds.add(id);
      fixedRegion.set(id, 'region:letters');
      nodes.push({
        id,
        label: ch.toUpperCase(),
        kind: 'keyword',
        weight: Math.min(6, 1 + Math.log2(1 + cnt)),
        freshness: 0.8,
        pinned: false,
        regionId: 'region:letters',
        sources: ['alphabet'],
        color: hsl(200),
      });
    }
  }

  // ── innate Language: top learned words ─────────────────────────────────────
  if (learner) {
    // Single O(n) pass: keep only reinforced words (count > 1) — this drops the huge
    // count==1 bulk vocabulary WITHOUT sorting ~700k entries every build (avoids lag),
    // and bulk words never make the top-N anyway. Then sort the small remainder.
    const reinforced: [string, { count: number; lastSeen: string; sources: string[] }][] = [];
    for (const e of learner.words) if (e[1].count > 1) reinforced.push(e);
    const topWords = reinforced.sort((a, b) => b[1].count - a[1].count).slice(0, MAX_LEX_NODES);
    for (const [w, meta] of topWords) {
      if (keywordNodeId.has(w)) continue; // already a personal keyword node
      const id = `lex_${w}`;
      baseIds.add(id);
      fixedRegion.set(id, 'region:language');
      keywordNodeId.set(w, id);
      nodes.push({
        id,
        label: w,
        kind: 'keyword',
        weight: Math.min(8, 1 + Math.log2(1 + meta.count)),
        freshness: freshnessOf(meta.lastSeen),
        pinned: false,
        regionId: 'region:language',
        sources: meta.sources.length ? meta.sources : ['learned'],
        color: hsl(150),
      });
    }
  }

  // ── skill region: Programming (always present from the curated corpus) ─────
  const PROG_REGION = 'region:programming';
  nodes.push({ id: PROG_REGION, label: 'Programming', kind: 'keyword', weight: 11, freshness: 1, pinned: true, regionId: PROG_REGION, sources: ['skill'], color: hsl(30, 80, 62) });
  baseIds.add(PROG_REGION);
  fixedRegion.set(PROG_REGION, PROG_REGION);
  const techHubId: Record<string, string> = {};
  for (const tech of TECHS) {
    const id = `prog:${tech}`;
    techHubId[tech] = id;
    baseIds.add(id);
    fixedRegion.set(id, PROG_REGION);
    nodes.push({ id, label: TECH_LABEL[tech], kind: 'keyword', weight: 6, freshness: 0.9, pinned: false, regionId: PROG_REGION, sources: ['skill'], color: hsl(30) });
  }
  const snippetNodes: { id: string; tech: string }[] = [];
  PROGRAMMING_SNIPPETS.slice(0, 800).forEach((sn, i) => { // every curated example is a visible doc neuron
    const id = `snip:${i}`;
    baseIds.add(id);
    fixedRegion.set(id, PROG_REGION);
    snippetNodes.push({ id, tech: sn.tech });
    nodes.push({ id, label: sn.title, kind: 'doc', weight: 4, freshness: 0.85, pinned: false, regionId: PROG_REGION, sources: [sn.source], color: hsl(30, 60, 55) });
  });

  // ── skill region: Web (learned from the internet via ingestWeb) ────────────
  const WEB_REGION = 'region:web';
  const webDocs = getWebDocs();
  const webNodeIds: string[] = [];
  if (webDocs.length) {
    nodes.push({ id: WEB_REGION, label: 'Web', kind: 'keyword', weight: 10, freshness: 1, pinned: true, regionId: WEB_REGION, sources: ['web'], color: hsl(320, 80, 62) });
    baseIds.add(WEB_REGION);
    fixedRegion.set(WEB_REGION, WEB_REGION);
    webDocs.slice(0, 200).forEach((d, i) => {
      const id = `web:${i}`;
      baseIds.add(id);
      fixedRegion.set(id, WEB_REGION);
      webNodeIds.push(id);
      nodes.push({ id, label: d.title.length > 40 ? `${d.title.slice(0, 40)}…` : d.title || d.url, kind: 'doc', weight: Math.min(8, d.weight + 1), freshness: 0.9, pinned: false, regionId: WEB_REGION, sources: [d.url], color: hsl(320, 60, 55) });
    });
  }

  // ── union-find: PERSONAL clustering only (base nodes + profile excluded) ────
  const parent = new Map<string, string>();
  const ensure = (k: string) => {
    if (!parent.has(k)) parent.set(k, k);
  };
  const find = (x: string): string => {
    let r = x;
    while (parent.get(r) !== r) {
      const p = parent.get(r);
      if (p === undefined) {
        parent.set(r, r);
        break;
      }
      r = p;
    }
    let cur = x;
    while (parent.get(cur) !== r) {
      const next = parent.get(cur)!;
      parent.set(cur, r);
      cur = next;
    }
    return r;
  };
  const isPersonal = (id: string) => !baseIds.has(id) && id !== 'profile';
  const union = (a: string, b: string) => {
    ensure(a);
    ensure(b);
    parent.set(find(a), find(b));
  };
  for (const n of nodes) if (isPersonal(n.id)) ensure(n.id);

  // ── edges ──────────────────────────────────────────────────────────────────
  const edges: BrainEdge[] = [];
  const seen = new Set<string>();
  const addEdge = (a: string, b: string, strength: number, fresh: boolean, dir: 0 | 1 = 0, cluster = true) => {
    if (a === b) return;
    const key = a < b ? `${a}|${b}` : `${b}|${a}`;
    if (seen.has(key)) return;
    seen.add(key);
    edges.push({ a, b, strength: clamp01(strength), dir, fresh });
    if (cluster && isPersonal(a) && isPersonal(b)) union(a, b);
  };

  // innate wiring: Letters → Language → Answering → Reasoning (directed, no cluster)
  addEdge('region:letters', 'region:language', 0.85, false, 1, false);
  addEdge('region:language', 'region:answering', 0.85, false, 1, false);
  addEdge('region:answering', 'region:reasoning', 0.8, false, 1, false);

  // programming skill region wiring (fixed; no clustering)
  addEdge('region:language', PROG_REGION, 0.7, false, 1, false);
  addEdge('region:answering', PROG_REGION, 0.7, false, 0, false);
  addEdge(PROG_REGION, 'region:reasoning', 0.7, false, 1, false);
  for (const tech of TECHS) addEdge(PROG_REGION, techHubId[tech], 0.5, false, 0, false);
  for (const s of snippetNodes) addEdge(techHubId[s.tech], s.id, 0.45, false, 0, false);

  // web skill region wiring (learned from the internet)
  if (webNodeIds.length) {
    addEdge('region:answering', WEB_REGION, 0.7, false, 0, false);
    addEdge(WEB_REGION, 'region:reasoning', 0.7, false, 1, false);
    addEdge('region:language', WEB_REGION, 0.6, false, 1, false);
    for (const id of webNodeIds) addEdge(WEB_REGION, id, 0.5, false, 0, false);
  }

  // region hubs → their member nodes
  for (const n of nodes) {
    const fr = fixedRegion.get(n.id);
    if ((fr === 'region:letters' || fr === 'region:language') && n.id !== fr) {
      addEdge(fr, n.id, 0.4, false, 0, false);
    }
  }

  // learned word→next-word associations (Markov), within the Language region
  if (learner) {
    for (const [w, nexts] of learner.transitions) {
      if (edges.length >= MAX_EDGES) break;
      const aId = keywordNodeId.get(w);
      if (!aId || !baseIds.has(aId)) continue;
      const maxN = Math.max(1, ...nexts.values());
      for (const [n2, c] of [...nexts.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3)) {
        const bId = keywordNodeId.get(n2);
        if (bId && baseIds.has(bId)) addEdge(aId, bId, 0.3 + (c / maxN) * 0.6, false, 1, false);
      }
    }
  }

  // personal membership + co-occurrence (cluster among personal; link to base
  // Language WITHOUT clustering, so personal memory sits on top of the base)
  const cooc = new Map<string, number>();
  for (const m of used) {
    if (m.kind === 'keyword') continue;
    const mid = idByMemory.get(m)!;
    const present = [...new Set(extractKeywords(m.content, 8))].filter((k) => keywordNodeId.has(k));
    present.slice(0, 4).forEach((k) => {
      const kid = keywordNodeId.get(k)!;
      addEdge(mid, kid, 0.3 + clamp01((m.weight ?? 1) / 10) * 0.5, freshnessOf(m.created_at) > 0.6, 0, !baseIds.has(kid));
    });
    for (let i = 0; i < present.length; i++)
      for (let j = i + 1; j < present.length; j++) {
        const x = present[i] < present[j] ? present[i] : present[j];
        const y = present[i] < present[j] ? present[j] : present[i];
        cooc.set(`${x}|${y}`, (cooc.get(`${x}|${y}`) ?? 0) + 1);
      }
  }
  const maxCo = Math.max(1, ...cooc.values());
  [...cooc.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, Math.max(0, MAX_EDGES - edges.length))
    .forEach(([pair, count]) => {
      const [x, y] = pair.split('|');
      const ax = keywordNodeId.get(x);
      const by = keywordNodeId.get(y);
      if (ax && by) addEdge(ax, by, 0.35 + (count / maxCo) * 0.65, false, 0, !baseIds.has(ax) && !baseIds.has(by));
    });

  // Reasoning pulls from the personal layer: the profile + a few top personal keywords
  if (hasProfile) addEdge('region:reasoning', 'profile', 0.7, false, 1, false);
  used
    .filter((m) => m.kind === 'keyword')
    .slice(0, 3)
    .forEach((m) => addEdge('region:reasoning', idByMemory.get(m)!, 0.45, false, 1, false));

  // ── regions ────────────────────────────────────────────────────────────────
  const regions: BrainRegion[] = INNATE.map((r) => ({
    id: r.id,
    label: r.label,
    hue: r.hue,
    centroid: r.centroid,
    nodeIds: [] as string[],
  }));
  const regionById = new Map(regions.map((r) => [r.id, r]));
  if (hasProfile) {
    const self: BrainRegion = { id: 'region:self', label: profile.name || 'You', hue: 190, centroid: [0, 0, 0], nodeIds: [] };
    regions.push(self);
    regionById.set('region:self', self);
  }
  const progRegion: BrainRegion = { id: PROG_REGION, label: 'Programming', hue: 30, centroid: [6.5, 3, 3.5], nodeIds: [] };
  regions.push(progRegion);
  regionById.set(PROG_REGION, progRegion);
  if (webNodeIds.length) {
    const webRegion: BrainRegion = { id: WEB_REGION, label: 'Web', hue: 320, centroid: [-6.5, -3, 3.5], nodeIds: [] };
    regions.push(webRegion);
    regionById.set(WEB_REGION, webRegion);
  }

  // base nodes → fixed regions; personal nodes → dynamic components
  const compNodes = new Map<string, BrainNode[]>();
  for (const n of nodes) {
    const fr = fixedRegion.get(n.id);
    if (fr) {
      n.regionId = fr;
      regionById.get(fr)?.nodeIds.push(n.id);
      continue;
    }
    if (n.id === 'profile') {
      n.regionId = 'region:self';
      regionById.get('region:self')?.nodeIds.push(n.id);
      continue;
    }
    const root = find(n.id);
    (compNodes.get(root) ?? compNodes.set(root, []).get(root)!).push(n);
  }
  let ri = 0;
  for (const [root, group] of compNodes) {
    const hue = (120 + ri * 53) % 360;
    ri++;
    const kw = group.filter((n) => n.kind === 'keyword').sort((a, b) => b.weight - a.weight)[0];
    const label = kw?.label ?? group.sort((a, b) => b.weight - a.weight)[0]?.label ?? 'cluster';
    for (const n of group) {
      n.regionId = root;
      n.color = hsl(hue);
    }
    regions.push({ id: root, label, hue, nodeIds: group.map((n) => n.id) });
  }

  // ── stats (over ALL memories) ──────────────────────────────────────────────
  const facts = memories.filter((m) => m.kind === 'fact').length;
  const keywords = memories.filter((m) => m.kind === 'keyword').length;
  const docs = memories.filter((m) => m.kind === 'doc' || m.kind === 'summary').length;
  const lastLearnedAt = memories.reduce<string | null>(
    (acc, m) => (m.created_at && (!acc || m.created_at > acc) ? m.created_at : acc),
    null,
  );

  const stats: BrainStats = {
    conversations,
    facts,
    keywords,
    docs,
    vocab: learner ? learner.vocabSize : keywords,
    fullnessPct: Math.min(100, Math.round((memories.length / FULLNESS_CAP) * 100)),
    lastLearnedAt,
  };

  return { graph: { nodes, edges, regions }, stats };
}
