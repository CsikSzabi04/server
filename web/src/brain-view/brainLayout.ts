// brainLayout.ts — lays the BrainGraph out into a real ANATOMICAL brain silhouette
// (side profile, BRAIN.md §34): a big bilobed CEREBRUM, a smaller CEREBELLUM lump
// at the back-bottom, and a BRAIN STEM stalk hanging down. Nodes fill these shells
// (surface-skewed so the form reads); a light REAL-edge relaxation tightens
// connected neighbours, then every node is snapped back into its part so the
// silhouette holds. Seeded + bounded → stable and fast at thousands of nodes.
import type { BrainGraph, Positions } from './types';

// ════════════════════════════════════════════════════════════════════════════
//  TUNING — every knob for the brain shape lives here. Edit a number, save, and
//  Vite HMR shows it live on /brain. Coords: X = width (the two hemispheres),
//  Y = up(+)/down(-), Z = front(+)/back(-). Bigger ellipsoid axis = bigger in
//  that direction. (None of this invents connections — it only positions nodes.)
// ════════════════════════════════════════════════════════════════════════════

// — PART PROPORTIONS — how the nodes split across the three anatomical parts.
//   These are cumulative thresholds on a 0..1 hash:
//   cerebrum = up to PART_CEREBELLUM, cerebellum = up to PART_STEM, stem = rest.
//   Current ≈ 85% cerebrum / 10% cerebellum / 5% stem.
const PART_CEREBELLUM = 0.85; // ↑ = more cerebrum (bigger main mass)
const PART_STEM = 0.95; // gap to 1.0 = stem share (now 5%); lower PART_STEM = bigger cerebellum

// — CEREBRUM (main mass) — center + half-axes. Bigger + taller (ay up) than a flat
//   pancake so it reads as a FULL brain spread out in 3D, not a thin disc.
const CB = { cx: 0, cy: 2.0, cz: 0, ax: 10.5, ay: 7.2, az: 12.5 };

// — CEREBELLUM (lump at back-bottom) — center (cy down, cz back) + half-axes (size).
const CE = { cx: 0, cy: -3.2, cz: -8.4, ax: 4.4, ay: 3.4, az: 5.0 };

// — BRAIN STEM (downward stalk) — top→bottom endpoints (length & angle) + radius.
const STEM_TOP: [number, number, number] = [0, -2.0, -3.8];
const STEM_BOT: [number, number, number] = [0, -10.5, -5.6]; // lower/more -z = longer & more angled
const STEM_R = 1.2; // thickness

// — SHELL THICKNESS — concentrate nodes near the SURFACE so the brain SILHOUETTE
//   reads (a hollow shell), instead of a solid glowing blob that hides the shape.
const SHELL_MIN = 0.66; // inner radius: 0 = solid/filled, →1 = thin hollow shell
const SHELL_SKEW = 0.28; // <1 pushes nodes toward the surface (the form)

// — MISC —
const FISSURE = 1.0; // half-gap between the two hemispheres (wider = clearer split)
const ITER = 10; // light force-relaxation iterations
const ATTRACT = 0.012; // edge pull — REAL learned edges only; small → silhouette holds

function seeded(id: string, salt: string): number {
  let h = 2166136261;
  const s = id + salt;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

function partOf(id: string): number {
  const r = seeded(id, 'part');
  if (r < PART_CEREBELLUM) return 0;
  if (r < PART_STEM) return 1;
  return 2;
}

// A surface-skewed point inside an ellipsoid (centered at origin), so most nodes
// sit near the shell (defines the form) with some interior strands.
function shellPoint(id: string, ax: number, ay: number, az: number): [number, number, number] {
  let x = (seeded(id, 'x') - 0.5) * 2 * ax;
  let y = (seeded(id, 'y') - 0.5) * 2 * ay;
  let z = (seeded(id, 'z') - 0.5) * 2 * az;
  const rr = Math.sqrt((x / ax) ** 2 + (y / ay) ** 2 + (z / az) ** 2) || 0.001;
  const target = SHELL_MIN + (1 - SHELL_MIN) * Math.pow(seeded(id, 's'), SHELL_SKEW);
  const sc = target / rr;
  x *= sc;
  y *= sc;
  z *= sc;
  return [x, y, z];
}

function clampEll(
  x: number, y: number, z: number,
  cx: number, cy: number, cz: number,
  ax: number, ay: number, az: number,
): [number, number, number] {
  const dx = (x - cx) / ax;
  const dy = (y - cy) / ay;
  const dz = (z - cz) / az;
  const rr = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (rr > 1) return [cx + (x - cx) / rr, cy + (y - cy) / rr, cz + (z - cz) / rr];
  return [x, y, z];
}

function snapStem(x: number, y: number, z: number): [number, number, number] {
  const y0 = STEM_TOP[1];
  const y1 = STEM_BOT[1]; // y1 < y0
  const yy = Math.max(y1, Math.min(y0, y));
  const t = (yy - y0) / (y1 - y0);
  const ax = STEM_TOP[0] + (STEM_BOT[0] - STEM_TOP[0]) * t;
  const az = STEM_TOP[2] + (STEM_BOT[2] - STEM_TOP[2]) * t;
  let dx = x - ax;
  let dz = z - az;
  const d = Math.sqrt(dx * dx + dz * dz);
  if (d > STEM_R) {
    dx = (dx / d) * STEM_R;
    dz = (dz / d) * STEM_R;
  }
  return [ax + dx, yy, az + dz];
}

function placePart(id: string, part: number): [number, number, number] {
  if (part === 2) {
    const t = seeded(id, 't');
    return [
      STEM_TOP[0] + (STEM_BOT[0] - STEM_TOP[0]) * t + (seeded(id, 'sx') - 0.5) * STEM_R,
      STEM_TOP[1] + (STEM_BOT[1] - STEM_TOP[1]) * t,
      STEM_TOP[2] + (STEM_BOT[2] - STEM_TOP[2]) * t + (seeded(id, 'sz') - 0.5) * STEM_R,
    ];
  }
  const e = part === 0 ? CB : CE;
  let [x, y, z] = shellPoint(id, e.ax, e.ay, e.az);
  if (part === 0 && y < 0) y *= 0.8; // cerebrum: rounded top, flatter underside
  return [x + e.cx, y + e.cy, z + e.cz];
}

function snapPart(x: number, y: number, z: number, part: number): [number, number, number] {
  if (part === 2) return snapStem(x, y, z);
  const e = part === 0 ? CB : CE;
  return clampEll(x, y, z, e.cx, e.cy, e.cz, e.ax, e.ay, e.az);
}

// Sculpt the cerebrum ellipsoid into a real brain profile (local coords, relative
// to the cerebrum center): a tapered/pointed occipital (back), a temporal lobe
// drooping at the lower front, and a flatter underside. Applied AFTER relaxation
// so the silhouette isn't pulled back to a plain egg shape.
function shapeCerebrum(x: number, y: number, z: number): [number, number, number] {
  const nz = z / CB.az; // +front .. -back
  if (nz < 0) {
    const t = 1 + 0.45 * nz; // narrow & round the back toward a point (occipital)
    x *= t;
    y *= t;
  }
  if (z > 0 && y < 0) {
    y *= 1 + 0.5 * (z / CB.az); // temporal lobe: lower front droops down
  }
  if (y < 0) y *= 0.85; // flatter underside
  return [x, y, z];
}

export function brainLayout(graph: BrainGraph): Positions {
  const nodes = graph.nodes;
  const N = nodes.length;
  if (N === 0) return {};

  const indexOf = new Map<string, number>();
  nodes.forEach((n, i) => indexOf.set(n.id, i));

  const parts = new Uint8Array(N);
  const pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const p = partOf(nodes[i].id);
    parts[i] = p;
    const [x, y, z] = placePart(nodes[i].id, p);
    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;
  }

  // ── light relaxation: nudge real-edge neighbours together, then snap each node
  //    back into its anatomical part so the brain shape is preserved ──
  const edges = graph.edges;
  for (let it = 0; it < ITER; it++) {
    for (let e = 0; e < edges.length; e++) {
      const a = indexOf.get(edges[e].a);
      const b = indexOf.get(edges[e].b);
      if (a == null || b == null) continue;
      const f = ATTRACT * (edges[e].strength ?? 0.3);
      const ax = a * 3;
      const bx = b * 3;
      const dx = pos[bx] - pos[ax];
      const dy = pos[bx + 1] - pos[ax + 1];
      const dz = pos[bx + 2] - pos[ax + 2];
      pos[ax] += dx * f;
      pos[ax + 1] += dy * f;
      pos[ax + 2] += dz * f;
      pos[bx] -= dx * f;
      pos[bx + 1] -= dy * f;
      pos[bx + 2] -= dz * f;
    }
    for (let i = 0; i < N; i++) {
      const [sx, sy, sz] = snapPart(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2], parts[i]);
      pos[i * 3] = sx;
      pos[i * 3 + 1] = sy;
      pos[i * 3 + 2] = sz;
    }
  }

  // ── split the two hemispheres (cerebrum + cerebellum; stem stays at midline) +
  //    recenter on the origin so the camera frames the brain ──
  const out: Positions = {};
  let mx = 0;
  let my = 0;
  let mz = 0;
  for (let i = 0; i < N; i++) {
    let x = pos[i * 3];
    let y = pos[i * 3 + 1];
    let z = pos[i * 3 + 2];
    if (parts[i] === 0) {
      // sculpt the cerebrum into a brain profile (in local coords, then re-center)
      const [sx, sy, sz] = shapeCerebrum(x - CB.cx, y - CB.cy, z - CB.cz);
      x = sx + CB.cx;
      y = sy + CB.cy;
      z = sz + CB.cz;
    }
    if (parts[i] !== 2) x += (x >= 0 ? 1 : -1) * FISSURE;
    out[nodes[i].id] = [x, y, z];
    mx += x;
    my += y;
    mz += z;
  }
  mx /= N;
  my /= N;
  mz /= N;
  for (const id in out) {
    const p = out[id];
    out[id] = [p[0] - mx, p[1] - my, p[2] - mz];
  }
  return out;
}
