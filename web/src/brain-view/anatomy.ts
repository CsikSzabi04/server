// anatomy.ts — the FORM of the brain and its FUNCTIONAL ATLAS (pure math, no React).
//
// Everything that decides "where is what" in the /brain view lives here, shared by
// the layout (nodes), the cortex shell mesh and the GLSL shaders:
//   • two hemispheres: sculpted ellipsoids with a temporal lobe, Sylvian fissure,
//     central sulcus, flat medial wall, and GYRI/SULCI from simplex noise,
//   • cerebellum (with folia) + brain stem,
//   • a functional atlas: real knowledge is placed in the lobe that matches what it
//     IS (programming docs → parietal, Wikipedia → temporal, …).
// Coords: X = left(-)/right(+), Y = up, Z = front(+)/back(-). Deterministic.
import type { BrainNode } from './types';

// ════════════════════════════════════════════════════════════════════════════
//  SHAPE KNOBS
// ════════════════════════════════════════════════════════════════════════════
/** One hemisphere: center offset + half-axes (lat = outward, med = toward midline). */
export const HEM = { cx: 6.1, cy: 3.0, lat: 7.8, med: 6.4, up: 9.6, down: 6.6, front: 15.4, back: 16.0, wall: 0.38 };
/** Cerebellum (both halves as one body, tucked under the occipital lobe). */
export const CBL = { cx: 0, cy: -5.0, cz: -11.6, ax: 8.0, ay: 4.1, az: 5.0 };
/** Brain stem: top (hidden inside) → bottom. */
export const STEM_TOP: [number, number, number] = [0, -0.5, -3.2];
export const STEM_BOT: [number, number, number] = [0, -15.0, -6.8];
/** Where the camera orbits around. */
export const BRAIN_CENTER: [number, number, number] = [0, -0.8, -1.2];
/** Gyri / sulci noise frequencies (world units). Shared with the shell shader. */
export const FOLD_F1 = 0.235;
export const FOLD_F2 = 0.47;
/** Thalamus — the relay at the center; growth starts near here. */
export const THALAMUS: [number, number, number] = [0, HEM.cy - 3.6, -1.6];

// ════════════════════════════════════════════════════════════════════════════
//  SIMPLEX NOISE — exact JS port of the Ashima/McEwan GLSL snoise(vec3), so the
//  layout (JS) and the cortex shader (GLSL, see SNOISE_GLSL) agree on where the
//  sulci are: neurons sit on the gyri, the shell draws the sulci lines.
// ════════════════════════════════════════════════════════════════════════════
const mod289 = (x: number): number => x - Math.floor(x * (1 / 289)) * 289;
const permute = (x: number): number => mod289((x * 34 + 1) * x);
const taylorInvSqrt = (r: number): number => 1.79284291400159 - 0.85373472095314 * r;
const NSX = 2 / 7;
const NSY = 0.5 / 7 - 1;
const NSZ = 1 / 7;

function gradDot(p: number, x: number, y: number, z: number): [number, number] {
  const j = p - 49 * Math.floor(p * NSZ * NSZ);
  const xi = Math.floor(j * NSZ);
  const yi = Math.floor(j - 7 * xi);
  const gx0 = xi * NSX + NSY;
  const gy0 = yi * NSX + NSY;
  const h = 1 - Math.abs(gx0) - Math.abs(gy0);
  const sh = h <= 0 ? -1 : 0;
  const gx = gx0 + (Math.floor(gx0) * 2 + 1) * sh;
  const gy = gy0 + (Math.floor(gy0) * 2 + 1) * sh;
  const norm = taylorInvSqrt(gx * gx + gy * gy + h * h);
  const m = Math.max(0.6 - (x * x + y * y + z * z), 0);
  const m2 = m * m;
  return [m2 * m2, (gx * x + gy * y + h * z) * norm];
}

export function snoise(vx: number, vy: number, vz: number): number {
  const C1 = 1 / 6;
  const C2 = 1 / 3;
  const s = (vx + vy + vz) * C2;
  let ix = Math.floor(vx + s);
  let iy = Math.floor(vy + s);
  let iz = Math.floor(vz + s);
  const t = (ix + iy + iz) * C1;
  const x0 = vx - ix + t;
  const y0 = vy - iy + t;
  const z0 = vz - iz + t;
  const gx = x0 >= y0 ? 1 : 0;
  const gy = y0 >= z0 ? 1 : 0;
  const gz = z0 >= x0 ? 1 : 0;
  const lx = 1 - gx;
  const ly = 1 - gy;
  const lz = 1 - gz;
  const i1x = Math.min(gx, lz);
  const i1y = Math.min(gy, lx);
  const i1z = Math.min(gz, ly);
  const i2x = Math.max(gx, lz);
  const i2y = Math.max(gy, lx);
  const i2z = Math.max(gz, ly);
  const x1 = x0 - i1x + C1;
  const y1 = y0 - i1y + C1;
  const z1 = z0 - i1z + C1;
  const x2 = x0 - i2x + C2;
  const y2 = y0 - i2y + C2;
  const z2 = z0 - i2z + C2;
  const x3 = x0 - 0.5;
  const y3 = y0 - 0.5;
  const z3 = z0 - 0.5;
  ix = mod289(ix);
  iy = mod289(iy);
  iz = mod289(iz);
  const p0 = permute(permute(permute(iz) + iy) + ix);
  const p1 = permute(permute(permute(iz + i1z) + iy + i1y) + ix + i1x);
  const p2 = permute(permute(permute(iz + i2z) + iy + i2y) + ix + i2x);
  const p3 = permute(permute(permute(iz + 1) + iy + 1) + ix + 1);
  const a = gradDot(p0, x0, y0, z0);
  const b = gradDot(p1, x1, y1, z1);
  const c = gradDot(p2, x2, y2, z2);
  const d = gradDot(p3, x3, y3, z3);
  return 42 * (a[0] * a[1] + b[0] * b[1] + c[0] * c[1] + d[0] * d[1]);
}

/** The same noise in GLSL (Ashima/McEwan, MIT) — injected into the shell shader. */
export const SNOISE_GLSL = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0);
  const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy));
  vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);
  vec3 l=1.0-g;
  vec3 i1=min(g.xyz,l.zxy);
  vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;
  vec3 x2=x0-i2+C.yyy;
  vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857;
  vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);
  vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy;
  vec4 y=y_*ns.x+ns.yyyy;
  vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);
  vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0;
  vec4 s1=floor(b1)*2.0+1.0;
  vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;
  vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);
  vec3 p1=vec3(a0.zw,h.y);
  vec3 p2=vec3(a1.xy,h.z);
  vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
  m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}
`;

const smoothstep = (a: number, b: number, x: number): number => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** 0 inside a sulcus (groove) → 1 on top of a gyrus (ridge). */
export function foldAt(x: number, y: number, z: number): number {
  const n1 = Math.abs(snoise(x * FOLD_F1, y * FOLD_F1, z * FOLD_F1));
  const n2 = Math.abs(snoise(x * FOLD_F2 + 17, y * FOLD_F2 + 17, z * FOLD_F2 + 17));
  return smoothstep(0, 0.3, n1) * 0.78 + smoothstep(0, 0.3, n2) * 0.22;
}

// ════════════════════════════════════════════════════════════════════════════
//  HEMISPHERE SURFACE
//  Local direction (dl, dy, dz): dl = LATERAL (outward), so both hemispheres share
//  one shape function and are mirrored into world space.
// ════════════════════════════════════════════════════════════════════════════
const gauss = (x: number, y: number, z: number, s: number): number => Math.exp(-(x * x + y * y + z * z) / (s * s));

function axes(dl: number, dy: number, dz: number): [number, number, number] {
  return [dl > 0 ? HEM.lat : HEM.med, dy > 0 ? HEM.up : HEM.down, dz > 0 ? HEM.front : HEM.back];
}

/** Ellipsoid-normalised coords ("u-space") of the surface point in direction d. */
export function uOf(dl: number, dy: number, dz: number, r: number): [number, number, number] {
  const [ax, ay, az] = axes(dl, dy, dz);
  return [(dl * r) / ax, (dy * r) / ay, (dz * r) / az];
}

/** Sylvian (lateral) fissure height in u-space, as a function of front/back. */
const sylvian = (uz: number): number => -0.06 - 0.24 * uz;
/** Central sulcus front/back position in u-space, as a function of height. */
const central = (uy: number): number => 0.06 - 0.22 * uy;

/** Distance from the hemisphere center to its (un-folded) surface, direction d. */
export function hemiRadius(dl: number, dy: number, dz: number): number {
  const [ax, ay, az] = axes(dl, dy, dz);
  let r = 1 / Math.sqrt((dl / ax) ** 2 + (dy / ay) ** 2 + (dz / az) ** 2);
  const ul = (dl * r) / ax;
  const uy = (dy * r) / ay;
  const uz = (dz * r) / az;
  let m = 1;
  m += 0.11 * gauss(ul - 0.62, uy + 0.55, uz - 0.28, 0.34); // temporal lobe bulges out & down
  m += 0.05 * gauss(ul - 0.15, uy + 0.25, uz + 0.95, 0.35); // fuller occipital pole
  m -= 0.1 * smoothstep(-0.3, -0.75, uy) * smoothstep(0.3, 0.75, uz) * (1 - 0.5 * smoothstep(0.4, 0.8, ul)); // flat orbital underside
  m -= 0.06 * smoothstep(-0.55, -0.95, uy) * smoothstep(0.2, -0.5, uz) * smoothstep(0.2, -0.4, ul); // medial underside tucks in
  if (ul > 0.05 && uz > -0.55 && uz < 0.66)
    m -= 0.075 * Math.exp(-(((uy - sylvian(uz)) / 0.075) ** 2)) * smoothstep(0.05, 0.45, ul); // Sylvian fissure
  if (uy > -0.25) m -= 0.032 * Math.exp(-(((uz - central(uy)) / 0.045) ** 2)) * smoothstep(-0.25, 0.1, uy); // central sulcus
  r *= m;
  if (dl < 0) r = Math.min(r, (HEM.cx - HEM.wall) / -dl); // flat medial wall (the fissure between hemispheres)
  return r;
}

/** Local direction → world point on (t=1) or inside (t<1) hemisphere h (-1 left, +1 right). */
export function hemiPoint(h: number, dl: number, dy: number, dz: number, r: number, t = 1): [number, number, number] {
  return [h * (HEM.cx + dl * r * t), HEM.cy + dy * r * t, dz * r * t];
}

// ════════════════════════════════════════════════════════════════════════════
//  FUNCTIONAL ATLAS
// ════════════════════════════════════════════════════════════════════════════
export type Cell = 'prefrontal' | 'inferiorFrontal' | 'parietal' | 'occipital' | 'temporalSup' | 'temporalInf';

/** Which lobe sub-region a surface point (u-space) belongs to. */
export function cellOfU(ul: number, uy: number, uz: number): Cell {
  if (uz < -0.6) return 'occipital';
  const ys = sylvian(uz);
  if (uy < ys && uz < 0.66 && ul > -0.35) return uy < ys - 0.36 ? 'temporalInf' : 'temporalSup';
  if (uz > central(uy)) return uz > 0.42 ? 'prefrontal' : 'inferiorFrontal';
  return 'parietal';
}

export type ZoneId = 'reasoning' | 'speech' | 'programming' | 'language' | 'world' | 'vision' | 'memory' | 'proto';

export interface ZoneDef {
  id: ZoneId;
  name: string; // what it does
  lobe: string; // where it is
  blurb: string; // what real knowledge lives here
  color: string;
  cell: Cell | null; // cortex cell (null = deep / everywhere)
}

export const ZONES: ZoneDef[] = [
  { id: 'reasoning', name: 'Reasoning', lobe: 'prefrontal', blurb: 'knowledge base · relations · distilled answers', color: '#b18cff', cell: 'prefrontal' },
  { id: 'speech', name: 'Answering', lobe: 'Broca · motor', blurb: 'conversation patterns', color: '#ff9a4a', cell: 'inferiorFrontal' },
  { id: 'programming', name: 'Programming', lobe: 'parietal', blurb: 'docs · snippets · tech hubs', color: '#33d6f2', cell: 'parietal' },
  { id: 'language', name: 'Language', lobe: 'temporal · upper', blurb: 'base vocabulary EN · HU · DE', color: '#3fe0a0', cell: 'temporalSup' },
  { id: 'world', name: 'World knowledge', lobe: 'temporal · lower', blurb: 'Wikipedia corpus · web', color: '#ff6fb5', cell: 'temporalInf' },
  { id: 'vision', name: 'Letters', lobe: 'occipital', blurb: 'alphabet · characters', color: '#7a8cff', cell: 'occipital' },
  { id: 'memory', name: 'Your memory', lobe: 'limbic', blurb: 'profile · facts · words from your chats', color: '#ffd166', cell: null },
  { id: 'proto', name: 'Proto-neurons', lobe: 'substrate', blurb: 'self-built synthetic tokens (not real knowledge)', color: '#5d6b85', cell: null },
];
export const ZONE_INDEX: Record<ZoneId, number> = Object.fromEntries(ZONES.map((z, i) => [z.id, i])) as Record<ZoneId, number>;
export const ZONE_BY_ID: Record<ZoneId, ZoneDef> = Object.fromEntries(ZONES.map((z) => [z.id, z])) as Record<ZoneId, ZoneDef>;
const CELL_ZONE: Record<Cell, ZoneId> = {
  prefrontal: 'reasoning',
  inferiorFrontal: 'speech',
  parietal: 'programming',
  temporalSup: 'language',
  temporalInf: 'world',
  occipital: 'vision',
};
export const zoneOfCell = (c: Cell): ZoneId => CELL_ZONE[c];

/** Where a node belongs, from what it IS (its region / where it was learned). */
export function classifyNode(n: BrainNode): ZoneId {
  const id = n.id;
  if (n.kind === 'profile' || n.regionId === 'region:self') return 'memory';
  if (id === 'region:reasoning') return 'reasoning';
  if (id === 'region:answering') return 'speech';
  if (id === 'region:language') return 'language';
  if (n.regionId === 'region:letters') return 'vision';
  if (n.regionId === 'region:programming') return 'programming';
  if (n.regionId === 'region:web') return 'world';
  const src = n.sources?.[0] ?? '';
  if (src.startsWith('bulk:')) return 'proto';
  if (!id.startsWith('lex_') && !id.startsWith('ltr_') && !id.startsWith('region:')) return 'memory'; // personal memories
  if (src === 'chat') return 'memory';
  if (src.startsWith('distill')) return 'reasoning';
  if (src.startsWith('web:')) return 'world';
  if (src.startsWith('seed:prog')) return 'programming';
  if (src.startsWith('seed:knowledge') || src.startsWith('seed:relations')) return 'reasoning';
  if (src.startsWith('seed:general')) return 'world';
  if (src.startsWith('seed:convo')) return 'speech';
  if (src.startsWith('seed:alphabet')) return 'vision';
  return 'language';
}

/** Human-readable provenance for a node's source tag. */
export function describeSource(src: string | undefined): string {
  if (!src) return 'unknown';
  if (/^https?:\/\//i.test(src)) {
    try {
      return new URL(src).hostname.replace(/^www\./, '');
    } catch {
      return src;
    }
  }
  const [a, b, c] = src.split(':');
  const lang = (x?: string) => (x ? x.toUpperCase() : '');
  switch (a) {
    case 'innate':
      return 'innate region';
    case 'skill':
      return 'skill hub';
    case 'alphabet':
      return 'alphabet';
    case 'profile':
      return 'your profile';
    case 'chat':
      return 'your conversations';
    case 'distill':
      return 'distilled from the model';
    case 'web':
      return 'learned from the web';
    case 'bulk':
      return b === 'self' ? 'self-built (synthetic)' : 'procedural vocabulary';
    case 'seed':
      if (b === 'general') return `Wikipedia corpus ${lang(c)}`.trim();
      if (b === 'prog') return c ? `programming docs · ${c}` : 'programming docs';
      if (b === 'knowledge') return 'curated knowledge base';
      if (b === 'relations') return `concept relations ${lang(c)}`.trim();
      if (b === 'convo') return `conversation patterns ${lang(c)}`.trim();
      if (b === 'alphabet') return 'alphabet';
      return `base language ${lang(b)}`.trim();
    default:
      return src;
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  SAMPLING (deterministic per node id)
// ════════════════════════════════════════════════════════════════════════════
export function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Small seeded PRNG (mulberry32). */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randDir(rand: () => number): [number, number, number] {
  const z = rand() * 2 - 1;
  const a = rand() * Math.PI * 2;
  const s = Math.sqrt(1 - z * z);
  return [s * Math.cos(a), s * Math.sin(a), z];
}

/** A point in the cortex of `cell` (any cell if null), on hemisphere h (0 = either).
 *  Depth t ∈ [tMin, tMax], skewed toward the surface; points near the surface avoid
 *  the sulci so the folds read as dark grooves between neuron-covered gyri. */
export function sampleCortex(
  rand: () => number,
  cell: Cell | null,
  h: number,
  tMin: number,
  tMax: number,
  skew: number,
): [number, number, number] {
  let fallback: [number, number, number] | null = null;
  for (let tries = 0; tries < 60; tries++) {
    const hh = h || (rand() < 0.5 ? -1 : 1);
    const [dl, dy, dz] = randDir(rand);
    const r = hemiRadius(dl, dy, dz);
    if (cell) {
      const [ul, uy, uz] = uOf(dl, dy, dz, r);
      if (cellOfU(ul, uy, uz) !== cell) continue;
    }
    const t = tMin + (tMax - tMin) * Math.pow(rand(), skew);
    const p = hemiPoint(hh, dl, dy, dz, r, t);
    if (!fallback) fallback = p;
    if (t > 0.86) {
      const s = hemiPoint(hh, dl, dy, dz, r, 1);
      if (foldAt(s[0], s[1], s[2]) < 0.52 + 0.3 * rand()) continue; // stay off the sulci
    }
    return p;
  }
  return fallback ?? hemiPoint(h || 1, 0, 0, 1, HEM.front * 0.5, 0.5);
}

/** The limbic "C": the cingulate/hippocampal arc curling around the deep center. */
export function sampleLimbic(rand: () => number): [number, number, number] {
  const h = rand() < 0.5 ? -1 : 1;
  const th = -0.2 * Math.PI + rand() * 1.42 * Math.PI;
  const r = 5.4 + (rand() - 0.5) * 1.8;
  return [h * (1.3 + rand() * 1.7), HEM.cy - 1.4 + r * Math.sin(th) * 0.72 + (rand() - 0.5) * 0.8, -1.2 + r * Math.cos(th)];
}

/** Cerebellum radius in (unit) direction d — with the midline vermis notch. */
export function cblRadius(dx: number, dy: number, dz: number): number {
  let r = 1 / Math.sqrt((dx / CBL.ax) ** 2 + (dy / CBL.ay) ** 2 + (dz / CBL.az) ** 2);
  r *= 1 - 0.07 * Math.exp(-(((dx * r) / CBL.ax / 0.1) ** 2)) * (dz < 0 ? 1 : 0.3);
  return r;
}

export function sampleCerebellum(rand: () => number): [number, number, number] {
  const [dx, dy, dz] = randDir(rand);
  const r = cblRadius(dx, dy, dz) * (0.4 + 0.56 * Math.pow(rand(), 0.55));
  return [CBL.cx + dx * r, CBL.cy + dy * r, CBL.cz + dz * r];
}

// ── zone anchors (surface points per zone & hemisphere) — labels, hubs, camera ──
export interface ZoneAnchor {
  surface: [number, number, number]; // on the cortex
  normal: [number, number, number]; // outward
}
function computeAnchors(): Record<ZoneId, ZoneAnchor[]> {
  // average the LATERAL-facing surface points of each lobe (weighted toward the side
  // faces), so a label sits in the middle of what you see from a side / 3-4 view
  const acc = new Map<string, { x: number; y: number; z: number; n: number }>();
  const rand = rng(1234);
  for (let i = 0; i < 12000; i++) {
    const [dl, dy, dz] = randDir(rand);
    const r = hemiRadius(dl, dy, dz);
    const [ul, uy, uz] = uOf(dl, dy, dz, r);
    if (ul < 0.15) continue;
    const c = cellOfU(ul, uy, uz);
    const wgt = ul * ul;
    const a = acc.get(c) ?? { x: 0, y: 0, z: 0, n: 0 };
    a.x += dl * r * wgt;
    a.y += dy * r * wgt;
    a.z += dz * r * wgt;
    a.n += wgt;
    acc.set(c, a);
  }
  const out = {} as Record<ZoneId, ZoneAnchor[]>;
  for (const z of ZONES) out[z.id] = [];
  for (const [cell, a] of acc) {
    const len = Math.hypot(a.x, a.y, a.z) || 1;
    const dl = a.x / len;
    const dy = a.y / len;
    const dz = a.z / len;
    const r = hemiRadius(dl, dy, dz);
    for (const h of [-1, 1]) {
      const s = hemiPoint(h, dl, dy, dz, r, 1);
      const nx = s[0] - h * HEM.cx;
      const ny = s[1] - HEM.cy;
      const nz = s[2];
      const nl = Math.hypot(nx, ny, nz) || 1;
      out[zoneOfCell(cell as Cell)].push({ surface: s, normal: [nx / nl, ny / nl, nz / nl] });
    }
  }
  const lim: [number, number, number] = [0, HEM.cy + 1.8, -1.2];
  out.memory.push({ surface: lim, normal: [0, 1, 0] });
  return out;
}
export const ZONE_ANCHORS: Record<ZoneId, ZoneAnchor[]> = computeAnchors();
