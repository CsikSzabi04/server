// brainLayout.ts — places every BrainGraph node into the ANATOMICAL brain
// (anatomy.ts): real knowledge goes to the lobe that matches what it is
// (programming docs → parietal, Wikipedia → temporal, your chats → limbic …);
// synthetic self-built tokens become a faint "proto" substrate.
//
// Placement is a pure function of (node id, zone), cached across rebuilds, so the
// brain never jumps when it grows: existing neurons stay put and new ones sprout
// in place. No edges are invented — this only decides positions.
import type { BrainGraph, BrainNode, Positions } from './types';
import { isWebNode } from './types';
import {
  HEM,
  THALAMUS,
  ZONES,
  ZONE_ANCHORS,
  ZONE_BY_ID,
  classifyNode,
  hashStr,
  rng,
  sampleCerebellum,
  sampleCortex,
  sampleLimbic,
  type ZoneId,
} from './anatomy';

export interface BrainLayout {
  positions: Positions;
  zones: Record<string, ZoneId>;
  /** displayed neurons per zone */
  counts: Record<ZoneId, number>;
}

// Region hubs sit a little below the cortex at their zone's anchor (one hemisphere).
const HUB_SIDE: Record<string, number> = {
  'region:reasoning': -1,
  'region:answering': -1,
  'region:language': -1,
  'region:letters': 1,
  'region:programming': 1,
  'region:web': 1,
};

const cache = new Map<string, [number, number, number]>();
const CACHE_MAX = 120_000;

function place(n: BrainNode, zone: ZoneId): [number, number, number] {
  const key = `${zone}|${n.id}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const rand = rng(hashStr(n.id));
  let p: [number, number, number];

  if (n.kind === 'profile') {
    p = [...THALAMUS];
  } else if (n.id in HUB_SIDE) {
    const side = HUB_SIDE[n.id];
    const a = ZONE_ANCHORS[zone].find((x) => Math.sign(x.surface[0]) === side) ?? ZONE_ANCHORS[zone][0];
    const cx = side * HEM.cx;
    p = a
      ? [cx + (a.surface[0] - cx) * 0.74, HEM.cy + (a.surface[1] - HEM.cy) * 0.74, a.surface[2] * 0.74]
      : [side * HEM.cx, HEM.cy, 0];
  } else if (zone === 'memory') {
    p = sampleLimbic(rand);
  } else if (zone === 'proto') {
    // substrate: fills the volume (white matter + cortex), a quarter in the cerebellum
    p = rand() < 0.24 ? sampleCerebellum(rand) : sampleCortex(rand, null, 0, 0.42, 0.97, 0.7);
  } else {
    const cell = ZONE_BY_ID[zone].cell;
    // world knowledge leans right, language leans left (lateralisation), rest bilateral
    const h = zone === 'language' ? (rand() < 0.7 ? -1 : 1) : zone === 'world' ? (rand() < 0.7 ? 1 : -1) : 0;
    const deep = isWebNode(n) ? 0.8 : 0.6;
    p = sampleCortex(rand, cell, h, deep, 0.965, 0.55);
  }

  if (cache.size > CACHE_MAX) cache.clear();
  cache.set(key, p);
  return p;
}

export function brainLayout(graph: BrainGraph): BrainLayout {
  const positions: Positions = {};
  const zones: Record<string, ZoneId> = {};
  const counts = Object.fromEntries(ZONES.map((z) => [z.id, 0])) as Record<ZoneId, number>;
  for (const n of graph.nodes) {
    const zone = classifyNode(n);
    zones[n.id] = zone;
    counts[zone]++;
    positions[n.id] = place(n, zone);
  }
  return { positions, zones, counts };
}
