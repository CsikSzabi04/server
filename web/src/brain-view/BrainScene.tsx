// BrainScene.tsx — the grown brain, in 3D.
//
//   • a glass CORTEX shell (two hemispheres, real gyri/sulci from the same noise the
//     layout uses), cerebellum with folia, brain stem rooted in a growth chamber;
//   • REAL knowledge as neurons, coloured by the lobe that holds it (anatomy.ts);
//     synthetic self-built tokens as a faint, optional proto substrate;
//   • white-matter FIBERS (the learned associations), arcing through the deep brain
//     and over the corpus callosum;
//   • IMPULSES travelling those real fibers — one golden "thought" chain walks the
//     associations word by word and is written out inside the brain (and reported
//     to the page HUD); asking the brain fires the words of the question;
//   • GROWTH: the brain sprouts from the stem outward on load, new neurons flash in.
// Brightness is bounded on purpose: normal blending everywhere, only impulses bloom.
import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { BrainGraph, BrainNode } from './types';
import { isWebNode } from './types';
import type { BrainLayout } from './brainLayout';
import {
  BRAIN_CENTER,
  CBL,
  FOLD_F1,
  FOLD_F2,
  HEM,
  SNOISE_GLSL,
  STEM_BOT,
  STEM_TOP,
  ZONES,
  ZONE_ANCHORS,
  ZONE_INDEX,
  cblRadius,
  cellOfU,
  foldAt,
  hashStr,
  hemiPoint,
  hemiRadius,
  uOf,
  zoneOfCell,
  type ZoneId,
} from './anatomy';

// ── knobs ──────────────────────────────────────────────────────────────────────
const HOME_DIR = new THREE.Vector3(-0.76, 0.2, 0.62).normalize(); // 3/4 view of the LEFT side (language)
const HOME_DIST = 47;
const INTRO_DIST = 84;
const MAX_FIBERS = 10000;
const CURVE_SEG = 6;
const PULSES = 96;
const TRAIL = 7;
const CHAIN_MAX = 8;
const PLATFORM_Y = STEM_BOT[1] - 1.4;
const GROW_SEED: [number, number, number] = [0, -3, -3.6]; // growth starts at the top of the stem

const ZCOL = ZONES.map((z) => new THREE.Color(z.color));
const WEB_COL = new THREE.Color('#ff4fd8');
const GOLD = new THREE.Color('#ffd166');
const SILVER = new THREE.Color('#9fb8d6');
const CENTER_V = new THREE.Vector3(...BRAIN_CENTER);
// orbit a bit BELOW the brain's center so it sits higher on screen, above the HUD
const CAM_TARGET = new THREE.Vector3(BRAIN_CENTER[0], BRAIN_CENTER[1] - 1.5, BRAIN_CENTER[2]);
const h01 = (s: string): number => (hashStr(s) % 100000) / 100000;
const f = (n: number): string => n.toFixed(4); // GLSL float literal

const STOP = new Set(
  (
    'the and for with that this from are was were have has had not but you your our their they them his her its ' +
    'into than then when what which who how why can will would could should there here also more most some such only ' +
    'other about over after before between each both very just like been being does did done one two new use used ' +
    'az egy és vagy de hogy nem is meg ki be el fel le mint csak már még ez ezt azt itt ott így úgy mert ha majd lesz ' +
    'volt van vannak minden nagyon sok kell lehet der die das und ist mit den dem des ein eine einer nicht sich auch ' +
    'auf für von zu im als wie aus bei nach oder wird sind werden wurde wurden einem einen eines dass zum zur ' +
    'ban ben nak nek val vel ról ről ból ből hoz hez tól től nál nél ra re ig ért ként egyik után alatt között szerint ' +
    'pedig illetve valamint amely amelyek amelyet amelyben aki akik ami amit volt lett mely több még ' +
    'which its many first second may might must where while these those'
  ).split(/\s+/),
);
const isConcept = (label: string): boolean =>
  label.length >= 3 && label.length <= 28 && !STOP.has(label.toLowerCase()) && !/^\d+$/.test(label);

export interface ThoughtStep {
  id: string;
  label: string;
  zone: ZoneId;
}
export interface FocusTarget {
  key: string;
  point: [number, number, number];
  kind: 'node' | 'zone';
}
export interface Stimulus {
  ids: string[];
  nonce: number;
}

// ════════════════════════════════════════════════════════════════════════════
//  MODEL — graph + layout → typed arrays the GPU and the impulse sim share
// ════════════════════════════════════════════════════════════════════════════
interface Fiber {
  a: number;
  b: number;
  s: number;
  c: [number, number, number] | null; // bezier control (null = straight, short)
  len: number;
  al: number; // base opacity (local fibres read stronger than long tracts)
  long: boolean; // long-range tract (drawn faint & silvery)
}
interface Model {
  real: BrainNode[];
  realIdx: Map<string, number>;
  zoneOf: ZoneId[];
  pos: Float32Array;
  color: Float32Array;
  size: Float32Array;
  born: Float32Array;
  zone: Float32Array;
  concept: Uint8Array;
  fire: Float32Array;
  fireActive: Set<number>;
  protoPos: Float32Array;
  protoBorn: Float32Array;
  fibers: Fiber[];
  adj: number[][];
  sprouts: number[]; // real neurons born after the intro (newly learned)
}

function fiberPoint(P: Float32Array, fb: Fiber, u: number, out: THREE.Vector3): THREE.Vector3 {
  const a = fb.a * 3;
  const b = fb.b * 3;
  if (!fb.c) return out.set(P[a] + (P[b] - P[a]) * u, P[a + 1] + (P[b + 1] - P[a + 1]) * u, P[a + 2] + (P[b + 2] - P[a + 2]) * u);
  const iu = 1 - u;
  const w0 = iu * iu;
  const w1 = 2 * iu * u;
  const w2 = u * u;
  return out.set(
    P[a] * w0 + fb.c[0] * w1 + P[b] * w2,
    P[a + 1] * w0 + fb.c[1] * w1 + P[b + 1] * w2,
    P[a + 2] * w0 + fb.c[2] * w1 + P[b + 2] * w2,
  );
}

function buildModel(
  graph: BrainGraph,
  layout: BrainLayout,
  births: Map<string, number>,
  now: number,
  introStart: number,
  reduced: boolean,
): Model {
  const real: BrainNode[] = [];
  const proto: BrainNode[] = [];
  for (const n of graph.nodes) {
    if (!layout.positions[n.id]) continue;
    (layout.zones[n.id] === 'proto' ? proto : real).push(n);
  }
  const R = real.length;
  const pos = new Float32Array(R * 3);
  const color = new Float32Array(R * 3);
  const size = new Float32Array(R);
  const born = new Float32Array(R);
  const zone = new Float32Array(R);
  const concept = new Uint8Array(R);
  const zoneOf: ZoneId[] = new Array(R);
  const realIdx = new Map<string, number>();
  const sprouts: number[] = [];
  const introOn = now - introStart < 7;

  const birth = (id: string, p: [number, number, number], isReal: boolean): [number, boolean] => {
    const known = births.get(id);
    if (known !== undefined) return [known, false];
    let b: number;
    let sprout = false;
    if (reduced) b = -100;
    else {
      const d = Math.hypot(p[0] - GROW_SEED[0], p[1] - GROW_SEED[1], p[2] - GROW_SEED[2]);
      const wave = introStart + 0.5 + (d / 26) * 3.8 + h01(id) * 0.6 + (isReal ? 0 : 0.9);
      if (introOn) b = Math.max(wave, now + 0.05 + h01(id) * 0.5);
      else {
        b = now + 0.2 + h01(id) * 1.8;
        sprout = true;
      }
    }
    births.set(id, b);
    return [b, sprout];
  };

  let maxW = 1;
  for (const n of real) if (n.kind !== 'profile' && !n.id.startsWith('region:')) maxW = Math.max(maxW, n.weight ?? 1);
  const tmp = new THREE.Color();
  real.forEach((n, i) => {
    const p = layout.positions[n.id];
    const z = layout.zones[n.id];
    pos[i * 3] = p[0];
    pos[i * 3 + 1] = p[1];
    pos[i * 3 + 2] = p[2];
    zoneOf[i] = z;
    zone[i] = ZONE_INDEX[z];
    const web = isWebNode(n);
    tmp.copy(web ? WEB_COL : ZCOL[ZONE_INDEX[z]]).multiplyScalar(0.72 + 0.36 * h01(n.id + 'c'));
    color[i * 3] = tmp.r;
    color[i * 3 + 1] = tmp.g;
    color[i * 3 + 2] = tmp.b;
    let s: number;
    if (n.kind === 'profile') s = 13;
    else if (n.id.startsWith('region:')) s = 11;
    else if (n.id.startsWith('prog:')) s = 6.5;
    else s = 2.1 + 5.4 * Math.min(1, (n.weight ?? 1) / maxW) + (n.pinned ? 2 : 0) + (web ? 2.5 : 0);
    size[i] = s;
    const [b, sprout] = birth(n.id, p, true);
    born[i] = b;
    concept[i] = isConcept(n.label) && !n.id.startsWith('ltr_') && !n.id.startsWith('region:') ? 1 : 0;
    if (sprout && concept[i]) sprouts.push(i);
    realIdx.set(n.id, i);
  });

  const protoPos = new Float32Array(proto.length * 3);
  const protoBorn = new Float32Array(proto.length);
  proto.forEach((n, i) => {
    const p = layout.positions[n.id];
    protoPos[i * 3] = p[0];
    protoPos[i * 3 + 1] = p[1];
    protoPos[i * 3 + 2] = p[2];
    protoBorn[i] = birth(n.id, p, false)[0];
  });

  // per lobe & hemisphere centroids → fibers between the same two lobes share one
  // waypoint, so they BUNDLE into tracts (like real white matter) instead of a hairball
  const cen = new Map<string, [number, number, number, number]>();
  for (let i = 0; i < R; i++) {
    const key = `${zone[i]}|${pos[i * 3] < 0 ? -1 : 1}`;
    const c = cen.get(key) ?? [0, 0, 0, 0];
    c[0] += pos[i * 3];
    c[1] += pos[i * 3 + 1];
    c[2] += pos[i * 3 + 2];
    c[3]++;
    cen.set(key, c);
  }
  const centroid = (i: number): [number, number, number] => {
    const c = cen.get(`${zone[i]}|${pos[i * 3] < 0 ? -1 : 1}`)!;
    return [c[0] / c[3], c[1] / c[3], c[2] / c[3]];
  };

  // fibers: learned associations between REAL neurons (strongest first). Local ones
  // (same lobe, same side, short) are drawn in colour; long-range tracts are capped
  // harder and drawn faint, so the lobes stay readable instead of a hairball.
  let nLocal = 0;
  let nLong = 0;
  const cand = graph.edges
    .filter((e) => e.a !== e.b && realIdx.has(e.a) && realIdx.has(e.b))
    .sort((x, y) => (y.strength ?? 0) - (x.strength ?? 0))
    .filter((e) => {
      const a = realIdx.get(e.a)!;
      const b = realIdx.get(e.b)!;
      const d = Math.hypot(pos[a * 3] - pos[b * 3], pos[a * 3 + 1] - pos[b * 3 + 1], pos[a * 3 + 2] - pos[b * 3 + 2]);
      const local = zone[a] === zone[b] && pos[a * 3] * pos[b * 3] > 0 && d < 7.5;
      if (local) return nLocal++ < MAX_FIBERS * 0.72;
      return nLong++ < MAX_FIBERS * 0.24;
    });
  const fibers: Fiber[] = [];
  const adj: number[][] = Array.from({ length: R }, () => []);
  const v = new THREE.Vector3();
  const w = new THREE.Vector3();
  for (const e of cand) {
    const a = realIdx.get(e.a)!;
    const b = realIdx.get(e.b)!;
    const ax = pos[a * 3];
    const ay = pos[a * 3 + 1];
    const az = pos[a * 3 + 2];
    const bx = pos[b * 3];
    const by = pos[b * 3 + 1];
    const bz = pos[b * 3 + 2];
    const len0 = Math.hypot(bx - ax, by - ay, bz - az);
    const st = e.strength ?? 0.3;
    const jit = (k: string) => (h01(e.a + e.b + k) - 0.5) * 1.1;
    let c: [number, number, number] | null = null;
    let al = 0.05 + 0.11 * st; // local (U-) fibers: the most visible
    const side = ax < 0 ? -1 : 1;
    if (len0 > 3.2) {
      if (ax * bx < 0 && Math.abs(ax) > 1.5 && Math.abs(bx) > 1.5) {
        // inter-hemispheric: arc over the corpus callosum
        const ca = centroid(a);
        const cb = centroid(b);
        c = [jit('x') * 0.4, HEM.cy + 1.6 + jit('y') * 0.5, Math.max(-8, Math.min(8, (ca[2] + cb[2]) / 2)) + jit('z')];
        al = 0.022 + 0.05 * st;
      } else if (zone[a] === zone[b]) {
        // within one lobe: a shallow U-fibre just under the cortex
        const hx = side * HEM.cx;
        c = [hx + ((ax + bx) / 2 - hx) * 0.8, HEM.cy + ((ay + by) / 2 - HEM.cy) * 0.8, ((az + bz) / 2) * 0.8];
      } else {
        // lobe → lobe: through the shared tract waypoint in the deep white matter
        const ca = centroid(a);
        const cb = centroid(b);
        const hx = side * HEM.cx * 0.55;
        const hy = HEM.cy - 0.8;
        c = [
          hx + ((ca[0] + cb[0]) / 2 - hx) * 0.4 + jit('x'),
          hy + ((ca[1] + cb[1]) / 2 - hy) * 0.4 + jit('y'),
          -0.6 + ((ca[2] + cb[2]) / 2 + 0.6) * 0.4 + jit('z'),
        ];
        al = 0.026 + 0.06 * st;
      }
    }
    const long = !(zone[a] === zone[b] && ax * bx > 0 && len0 < 7.5);
    if (long) al = 0.014 + 0.032 * st;
    const fb: Fiber = { a, b, s: st, c, len: len0, al, long };
    if (c) {
      let L = 0;
      fiberPoint(pos, fb, 0, v);
      for (let k = 1; k <= 8; k++) {
        fiberPoint(pos, fb, k / 8, w);
        L += v.distanceTo(w);
        v.copy(w);
      }
      fb.len = L;
    }
    adj[a].push(fibers.length);
    adj[b].push(fibers.length);
    fibers.push(fb);
  }

  return {
    real,
    realIdx,
    zoneOf,
    pos,
    color,
    size,
    born,
    zone,
    concept,
    fire: new Float32Array(R),
    fireActive: new Set(),
    protoPos,
    protoBorn,
    fibers,
    adj,
    sprouts,
  };
}

// ════════════════════════════════════════════════════════════════════════════
//  SHARED UNIFORMS
// ════════════════════════════════════════════════════════════════════════════
interface Uniforms {
  uTime: { value: number };
  uPR: { value: number };
  uScale: { value: number };
  uFocusZone: { value: number };
  uScanY: { value: number };
  uCamDist: { value: number };
  uReveal: { value: number };
}

// ── neurons ──────────────────────────────────────────────────────────────────
const NEURON_VERT = /* glsl */ `
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aBorn;
  attribute float aZone;
  attribute float aFire;
  attribute float aDim;
  uniform float uTime;
  uniform float uPR;
  uniform float uScale;
  uniform float uFocusZone;
  uniform float uScanY;
  uniform float uCamDist;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vFire;
  void main() {
    float age = uTime - aBorn;
    float grow = smoothstep(0.0, 0.9, age);
    float flash = age > 0.0 ? 1.0 - smoothstep(0.0, 1.6, age) : 0.0;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float depth = max(0.5, -mv.z);
    float fade = 1.0 - 0.6 * smoothstep(uCamDist - 10.0, uCamDist + 16.0, depth);
    float focus = uFocusZone < -0.5 ? 1.0 : (abs(aZone - uFocusZone) < 0.5 ? 1.3 : 0.12);
    float scan = exp(-pow((position.y - uScanY) / 0.8, 2.0));
    float hi = aDim > 1.0 ? 1.0 : 0.0;
    vFire = max(aFire, flash) + scan * 0.45 + hi * 0.6;
    vColor = aColor;
    vAlpha = grow * fade * focus * min(aDim, 1.0);
    float tw = 0.88 + 0.12 * sin(uTime * 1.4 + aBorn * 31.0);
    gl_PointSize = aSize * grow * tw * (1.0 + 0.8 * vFire + hi) * uPR * (uScale / depth);
    gl_Position = projectionMatrix * mv;
  }
`;
const NEURON_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  varying float vFire;
  void main() {
    if (vAlpha < 0.01) discard;
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    float core = smoothstep(0.26, 0.04, d);
    float halo = smoothstep(0.5, 0.12, d);
    vec3 col = vColor * (0.45 + 0.75 * core) + vec3(1.0, 0.9, 0.72) * vFire * core * 1.9;
    gl_FragColor = vec4(col, min(1.0, (core * 0.92 + halo * 0.22) * vAlpha));
  }
`;

function Neurons({
  model,
  uniforms,
  highlightIds,
  onHover,
  onSelect,
}: {
  model: Model;
  uniforms: Uniforms;
  highlightIds: Set<string> | null;
  onHover: (n: BrainNode | null, x: number, y: number) => void;
  onSelect: (n: BrainNode | null) => void;
}) {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { ...uniforms },
        vertexShader: NEURON_VERT,
        fragmentShader: NEURON_FRAG,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
      }),
    [uniforms],
  );
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const R = model.real.length;
    g.setAttribute('position', new THREE.BufferAttribute(model.pos, 3));
    g.setAttribute('aColor', new THREE.BufferAttribute(model.color, 3));
    g.setAttribute('aSize', new THREE.BufferAttribute(model.size, 1));
    g.setAttribute('aBorn', new THREE.BufferAttribute(model.born, 1));
    g.setAttribute('aZone', new THREE.BufferAttribute(model.zone, 1));
    g.setAttribute('aFire', new THREE.BufferAttribute(model.fire, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aDim', new THREE.BufferAttribute(new Float32Array(R).fill(1), 1).setUsage(THREE.DynamicDrawUsage));
    g.computeBoundingSphere();
    return g;
  }, [model]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);
  // leaving /brain while hovering a neuron must not leave the pointer cursor behind
  useEffect(
    () => () => {
      document.body.style.cursor = '';
    },
    [],
  );

  // search highlight: matches glow, the rest dims
  useEffect(() => {
    const attr = geometry.getAttribute('aDim') as THREE.BufferAttribute;
    const arr = attr.array as Float32Array;
    if (!highlightIds) arr.fill(1);
    else model.real.forEach((n, i) => (arr[i] = highlightIds.has(n.id) ? 1.6 : 0.12));
    attr.needsUpdate = true;
  }, [geometry, highlightIds, model]);

  // impulses ignite neurons; the glow decays here
  useFrame((_, dt) => {
    if (model.fireActive.size === 0) return;
    const k = Math.exp(-dt * 2.6);
    for (const i of model.fireActive) {
      model.fire[i] *= k;
      if (model.fire[i] < 0.02) {
        model.fire[i] = 0;
        model.fireActive.delete(i);
      }
    }
    (geometry.getAttribute('aFire') as THREE.BufferAttribute).needsUpdate = true;
  });

  return (
    <points
      geometry={geometry}
      material={material}
      renderOrder={4}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        const n = e.index != null ? model.real[e.index] : null;
        if (n) {
          document.body.style.cursor = 'pointer';
          onHover(n, e.nativeEvent.clientX, e.nativeEvent.clientY);
        }
      }}
      onPointerOut={() => {
        document.body.style.cursor = '';
        onHover(null, 0, 0);
      }}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        if (e.delta > 4) return; // that was a drag (rotating), not a click
        const n = e.index != null ? model.real[e.index] : null;
        if (n) onSelect(n);
      }}
    />
  );
}

// ── proto substrate (synthetic tokens): faint, non-interactive ──────────────────
const PROTO_VERT = /* glsl */ `
  attribute float aBorn;
  uniform float uTime;
  uniform float uPR;
  uniform float uScale;
  uniform float uFocusZone;
  uniform float uScanY;
  uniform float uCamDist;
  varying float vA;
  varying float vScan;
  void main() {
    float grow = smoothstep(0.0, 1.2, uTime - aBorn);
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float depth = max(0.5, -mv.z);
    float fade = 1.0 - 0.7 * smoothstep(uCamDist - 10.0, uCamDist + 16.0, depth);
    float focus = uFocusZone < -0.5 ? 1.0 : 0.25;
    float scan = exp(-pow((position.y - uScanY) / 0.8, 2.0));
    vScan = scan;
    vA = grow * fade * focus * (0.3 + scan * 0.5);
    gl_PointSize = 1.7 * grow * (1.0 + scan) * uPR * (uScale / depth);
    gl_Position = projectionMatrix * mv;
  }
`;
const PROTO_FRAG = /* glsl */ `
  uniform vec3 uColor;
  varying float vA;
  varying float vScan;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5 || vA < 0.01) discard;
    float core = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(uColor + vScan * vec3(0.15, 0.5, 0.7), core * vA);
  }
`;

function ProtoNeurons({ model, uniforms, visible }: { model: Model; uniforms: Uniforms; visible: boolean }) {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { ...uniforms, uColor: { value: ZCOL[ZONE_INDEX.proto].clone() } },
        vertexShader: PROTO_VERT,
        fragmentShader: PROTO_FRAG,
        transparent: true,
        depthWrite: false,
      }),
    [uniforms],
  );
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(model.protoPos, 3));
    g.setAttribute('aBorn', new THREE.BufferAttribute(model.protoBorn, 1));
    g.computeBoundingSphere();
    return g;
  }, [model]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(() => () => material.dispose(), [material]);
  return <points geometry={geometry} material={material} visible={visible} renderOrder={3} raycast={() => null} />;
}

// ── fibers (white matter) ────────────────────────────────────────────────────
const FIBER_VERT = /* glsl */ `
  attribute vec3 aColor;
  attribute float aAlpha;
  attribute float aBorn;
  attribute float aZa;
  attribute float aZb;
  uniform float uTime;
  uniform float uFocusZone;
  uniform float uCamDist;
  varying vec3 vColor;
  varying float vA;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float grow = smoothstep(0.0, 1.4, uTime - aBorn);
    float fade = 1.0 - 0.7 * smoothstep(uCamDist - 10.0, uCamDist + 16.0, -mv.z);
    bool inZ = abs(aZa - uFocusZone) < 0.5 || abs(aZb - uFocusZone) < 0.5;
    float focus = uFocusZone < -0.5 ? 1.0 : (inZ ? 1.8 : 0.12);
    vA = aAlpha * grow * fade * focus;
    vColor = aColor;
    gl_Position = projectionMatrix * mv;
  }
`;
const FIBER_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vA;
  void main() {
    if (vA < 0.004) discard;
    gl_FragColor = vec4(vColor, vA);
  }
`;

function buildFiberGeometry(m: Model, only: number[] | null, tint: THREE.Color | null, alphaK: number): THREE.BufferGeometry {
  const list = only ?? m.fibers.map((_, i) => i);
  let verts = 0;
  for (const i of list) verts += (m.fibers[i].c ? CURVE_SEG : 1) * 2;
  const pos = new Float32Array(verts * 3);
  const col = new Float32Array(verts * 3);
  const alpha = new Float32Array(verts);
  const born = new Float32Array(verts);
  const za = new Float32Array(verts);
  const zb = new Float32Array(verts);
  const p = new THREE.Vector3();
  const ca = new THREE.Color();
  const cb = new THREE.Color();
  const cc = new THREE.Color();
  let o = 0;
  for (const i of list) {
    const fb = m.fibers[i];
    if (tint) {
      ca.copy(tint);
      cb.copy(tint);
    } else {
      ca.copy(ZCOL[m.zone[fb.a]]).multiplyScalar(0.85);
      cb.copy(ZCOL[m.zone[fb.b]]).multiplyScalar(0.85);
      if (fb.long) {
        ca.lerp(SILVER, 0.6);
        cb.lerp(SILVER, 0.6);
      }
    }
    const al = Math.min(0.9, fb.al * alphaK);
    const bo = Math.max(m.born[fb.a], m.born[fb.b]) + 0.35;
    const segs = fb.c ? CURVE_SEG : 1;
    for (let k = 0; k < segs; k++) {
      for (const u of [k / segs, (k + 1) / segs]) {
        fiberPoint(m.pos, fb, u, p);
        cc.copy(ca).lerp(cb, u);
        pos[o * 3] = p.x;
        pos[o * 3 + 1] = p.y;
        pos[o * 3 + 2] = p.z;
        col[o * 3] = cc.r;
        col[o * 3 + 1] = cc.g;
        col[o * 3 + 2] = cc.b;
        alpha[o] = al;
        born[o] = bo;
        za[o] = m.zone[fb.a];
        zb[o] = m.zone[fb.b];
        o++;
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
  g.setAttribute('aAlpha', new THREE.BufferAttribute(alpha, 1));
  g.setAttribute('aBorn', new THREE.BufferAttribute(born, 1));
  g.setAttribute('aZa', new THREE.BufferAttribute(za, 1));
  g.setAttribute('aZb', new THREE.BufferAttribute(zb, 1));
  g.computeBoundingSphere();
  return g;
}

function useFiberMaterial(uniforms: Uniforms, additive: boolean): THREE.ShaderMaterial {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { ...uniforms },
        vertexShader: FIBER_VERT,
        fragmentShader: FIBER_FRAG,
        transparent: true,
        depthWrite: false,
        blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
      }),
    [uniforms, additive],
  );
  useEffect(() => () => mat.dispose(), [mat]);
  return mat;
}

function Fibers({ model, uniforms }: { model: Model; uniforms: Uniforms }) {
  const material = useFiberMaterial(uniforms, false);
  const geometry = useMemo(() => buildFiberGeometry(model, null, null, 1), [model]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <lineSegments geometry={geometry} material={material} renderOrder={2} raycast={() => null} />;
}

function SelectedFibers({ model, uniforms, selectedId }: { model: Model; uniforms: Uniforms; selectedId: string | null }) {
  const material = useFiberMaterial(uniforms, true);
  const geometry = useMemo(() => {
    const i = selectedId != null ? model.realIdx.get(selectedId) : undefined;
    if (i === undefined) return null;
    return buildFiberGeometry(model, model.adj[i], GOLD, 5.5);
  }, [model, selectedId]);
  useEffect(() => () => geometry?.dispose(), [geometry]);
  if (!geometry) return null;
  return <lineSegments geometry={geometry} material={material} renderOrder={5} raycast={() => null} />;
}

// ── cortex / cerebellum / stem: one glass shader, three modes ────────────────
const SHELL_VERT = /* glsl */ `
  attribute vec3 aBase;
  attribute vec3 aTint;
  attribute float aZone;
  varying vec3 vN;
  varying vec3 vWorld;
  varying vec3 vBase;
  varying vec3 vTint;
  varying float vZone;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vWorld = wp.xyz;
    vN = normalize(mat3(modelMatrix) * normal);
    vBase = aBase;
    vTint = aTint;
    vZone = aZone;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;
const SHELL_FRAG = /* glsl */ `
  uniform float uReveal;
  uniform float uFocusZone;
  uniform float uScanY;
  uniform float uMode;
  varying vec3 vN;
  varying vec3 vWorld;
  varying vec3 vBase;
  varying vec3 vTint;
  varying float vZone;
  ${SNOISE_GLSL}
  void main() {
    vec3 N = normalize(vN);
    vec3 V = normalize(cameraPosition - vWorld);
    float fres = pow(1.0 - abs(dot(N, V)), 2.3);
    float line = 0.0;
    float fold = 1.0;
    if (uMode < 0.5) {
      // cortex: sulci = zero-crossings of the SAME noise the layout uses
      float n1 = snoise(vBase * ${f(FOLD_F1)});
      float n2 = snoise(vBase * ${f(FOLD_F2)} + vec3(17.0));
      float w1 = max(fwidth(n1), 0.012);
      float w2 = max(fwidth(n2), 0.012);
      line = 1.0 - smoothstep(w1 * 0.6, w1 * 2.4, abs(n1));
      line = max(line, (1.0 - smoothstep(w2 * 0.6, w2 * 2.4, abs(n2))) * 0.38);
      fold = smoothstep(0.0, 0.3, abs(n1));
    } else if (uMode < 1.5) {
      // cerebellum: folia — fine transverse ridges
      float phi = atan(vBase.y - (${f(CBL.cy)}), -(vBase.z - (${f(CBL.cz)})));
      float st = abs(sin(phi * 30.0));
      float w = max(fwidth(st), 0.02);
      line = 1.0 - smoothstep(w * 0.6, w * 2.6, st);
      fold = smoothstep(0.0, 0.7, st);
    } else {
      // brain stem: longitudinal nerve tracts running down into the chamber
      float tt = clamp((${f(STEM_TOP[1])} - vBase.y) / ${f(STEM_TOP[1] - STEM_BOT[1])}, 0.0, 1.0);
      vec2 axis = mix(vec2(${f(STEM_TOP[0])}, ${f(STEM_TOP[2])}), vec2(${f(STEM_BOT[0])}, ${f(STEM_BOT[2])}), tt);
      float st = abs(sin(atan(vBase.x - axis.x, vBase.z - axis.y) * 9.0));
      float w = max(fwidth(st), 0.02);
      line = (1.0 - smoothstep(w * 0.6, w * 3.0, st)) * 0.7;
      fold = 0.7;
    }
    vec3 L = normalize(vec3(-0.35, 0.85, 0.4));
    float lam = 0.5 + 0.5 * max(dot(N, L), 0.0);
    vec3 base = mix(vec3(0.34, 0.5, 0.7), vTint, 0.55);
    float focus = uFocusZone < -0.5 ? 1.0 : (abs(vZone - uFocusZone) < 0.5 ? 2.4 : 0.4);
    float scan = exp(-pow((vWorld.y - uScanY) / 1.0, 2.0));
    float a = (0.014 + 0.16 * fres) * (0.55 + 0.45 * fold) * lam;
    a += line * (0.07 + 0.17 * fres) * lam;
    a += scan * (0.025 + 0.22 * line);
    float stemFade = uMode > 1.5 ? smoothstep(${f(STEM_BOT[1] + 0.5)}, ${f(STEM_BOT[1] + 5.0)}, vWorld.y) : 1.0;
    a *= focus * uReveal * stemFade;
    vec3 col = base * (0.75 + 0.6 * line) + vec3(0.35, 0.85, 1.0) * scan * 0.5;
    gl_FragColor = vec4(col, a);
  }
`;

// Average zone colour around a cortex point (soft lobe boundaries on the glass).
const TINT_OFFS: [number, number, number][] = [
  [0, 0, 0],
  [0.07, 0, 0],
  [-0.07, 0, 0],
  [0, 0.07, 0],
  [0, -0.07, 0],
  [0, 0, 0.07],
  [0, 0, -0.07],
];
function buildHemisphere(h: 1 | -1): THREE.BufferGeometry {
  let g: THREE.BufferGeometry = new THREE.SphereGeometry(1, 220, 150);
  g.deleteAttribute('uv');
  g.deleteAttribute('normal');
  g = mergeVertices(g);
  const P = g.getAttribute('position') as THREE.BufferAttribute;
  const n = P.count;
  const base = new Float32Array(n * 3);
  const tint = new Float32Array(n * 3);
  const zone = new Float32Array(n);
  const c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    // rotate the sphere so its poles point lateral / medial (pinching stays hidden)
    const dl = P.getY(i);
    const dy = -P.getX(i);
    const dz = P.getZ(i);
    const r = hemiRadius(dl, dy, dz);
    const s = hemiPoint(h, dl, dy, dz, r, 1);
    base[i * 3] = s[0];
    base[i * 3 + 1] = s[1];
    base[i * 3 + 2] = s[2];
    const k = 1 + 0.032 * (foldAt(s[0], s[1], s[2]) - 0.62); // gyri bulge, sulci sink
    const d = hemiPoint(h, dl, dy, dz, r * k, 1);
    P.setXYZ(i, d[0], d[1], d[2]);
    const [ul, uy, uz] = uOf(dl, dy, dz, r);
    let cr = 0;
    let cg = 0;
    let cb = 0;
    for (const o of TINT_OFFS) {
      c.copy(ZCOL[ZONE_INDEX[zoneOfCell(cellOfU(ul + o[0], uy + o[1], uz + o[2]))]]);
      cr += c.r;
      cg += c.g;
      cb += c.b;
    }
    const medial = ul < -0.3 ? 0.35 : 1; // the hidden medial wall stays neutral
    tint[i * 3] = (cr / TINT_OFFS.length) * medial + 0.3 * (1 - medial);
    tint[i * 3 + 1] = (cg / TINT_OFFS.length) * medial + 0.42 * (1 - medial);
    tint[i * 3 + 2] = (cb / TINT_OFFS.length) * medial + 0.6 * (1 - medial);
    zone[i] = ZONE_INDEX[zoneOfCell(cellOfU(ul, uy, uz))];
  }
  if (h < 0) {
    // mirrored hemisphere → flip triangle winding so FrontSide still faces out
    const idx = g.getIndex()!;
    for (let t = 0; t < idx.count; t += 3) {
      const b = idx.getX(t + 1);
      idx.setX(t + 1, idx.getX(t + 2));
      idx.setX(t + 2, b);
    }
  }
  g.setAttribute('aBase', new THREE.BufferAttribute(base, 3));
  g.setAttribute('aTint', new THREE.BufferAttribute(tint, 3));
  g.setAttribute('aZone', new THREE.BufferAttribute(zone, 1));
  g.computeVertexNormals();
  g.computeBoundingSphere();
  return g;
}

function buildCerebellum(): THREE.BufferGeometry {
  let g: THREE.BufferGeometry = new THREE.SphereGeometry(1, 160, 110);
  g.deleteAttribute('uv');
  g.deleteAttribute('normal');
  g = mergeVertices(g);
  const P = g.getAttribute('position') as THREE.BufferAttribute;
  const n = P.count;
  const base = new Float32Array(n * 3);
  const tint = new Float32Array(n * 3);
  const zone = new Float32Array(n).fill(-9);
  for (let i = 0; i < n; i++) {
    const dx = P.getX(i);
    const dy = P.getY(i);
    const dz = P.getZ(i);
    const r = cblRadius(dx, dy, dz);
    const bx = CBL.cx + dx * r;
    const by = CBL.cy + dy * r;
    const bz = CBL.cz + dz * r;
    base.set([bx, by, bz], i * 3);
    const k = 1 + 0.018 * Math.sin(Math.atan2(dy, -dz) * 30);
    P.setXYZ(i, CBL.cx + dx * r * k, CBL.cy + dy * r * k, CBL.cz + dz * r * k);
    tint.set([0.36, 0.5, 0.66], i * 3);
  }
  g.setAttribute('aBase', new THREE.BufferAttribute(base, 3));
  g.setAttribute('aTint', new THREE.BufferAttribute(tint, 3));
  g.setAttribute('aZone', new THREE.BufferAttribute(zone, 1));
  g.computeVertexNormals();
  return g;
}

function buildStem(): THREE.BufferGeometry {
  const g = new THREE.CylinderGeometry(1, 1, 1, 48, 40, true);
  g.deleteAttribute('uv');
  const P = g.getAttribute('position') as THREE.BufferAttribute;
  const n = P.count;
  for (let i = 0; i < n; i++) {
    const t = 0.5 - P.getY(i); // 0 top → 1 bottom
    const x = P.getX(i);
    const z = P.getZ(i);
    const cx = STEM_TOP[0] + (STEM_BOT[0] - STEM_TOP[0]) * t;
    const cy = STEM_TOP[1] + (STEM_BOT[1] - STEM_TOP[1]) * t;
    const cz = STEM_TOP[2] + (STEM_BOT[2] - STEM_TOP[2]) * t;
    const pons = 1 + 0.38 * Math.exp(-(((t - 0.27) / 0.11) ** 2)) * (z > 0 ? 1 : 0.45);
    const r = (2.4 + (1.45 - 2.4) * t) * pons;
    P.setXYZ(i, cx + x * r, cy, cz + z * r * 0.88);
  }
  g.setAttribute('aBase', new THREE.BufferAttribute(new Float32Array(P.array as Float32Array), 3));
  g.setAttribute('aTint', new THREE.BufferAttribute(new Float32Array(n * 3).fill(0.42), 3));
  g.setAttribute('aZone', new THREE.BufferAttribute(new Float32Array(n).fill(-9), 1));
  g.computeVertexNormals();
  return g;
}

function BrainShell({ uniforms }: { uniforms: Uniforms }) {
  const geos = useMemo(() => ({ l: buildHemisphere(-1), r: buildHemisphere(1), cbl: buildCerebellum(), stem: buildStem() }), []);
  const mats = useMemo(
    () =>
      [0, 1, 2].map(
        (mode) =>
          new THREE.ShaderMaterial({
            uniforms: { uReveal: uniforms.uReveal, uFocusZone: uniforms.uFocusZone, uScanY: uniforms.uScanY, uMode: { value: mode } },
            vertexShader: SHELL_VERT,
            fragmentShader: SHELL_FRAG,
            transparent: true,
            depthWrite: false,
            side: THREE.FrontSide,
          }),
      ),
    [uniforms],
  );
  useEffect(
    () => () => {
      Object.values(geos).forEach((g) => g.dispose());
      mats.forEach((m) => m.dispose());
    },
    [geos, mats],
  );
  return (
    <group>
      <mesh geometry={geos.l} material={mats[0]} renderOrder={6} raycast={() => null} />
      <mesh geometry={geos.r} material={mats[0]} renderOrder={6} raycast={() => null} />
      <mesh geometry={geos.cbl} material={mats[1]} renderOrder={6} raycast={() => null} />
      <mesh geometry={geos.stem} material={mats[2]} renderOrder={6} raycast={() => null} />
    </group>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//  IMPULSES + THOUGHT CHAIN
// ════════════════════════════════════════════════════════════════════════════
const PULSE_VERT = /* glsl */ `
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aAlpha;
  uniform float uPR;
  uniform float uScale;
  varying vec3 vColor;
  varying float vA;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float depth = max(0.5, -mv.z);
    vColor = aColor;
    vA = aAlpha;
    gl_PointSize = aSize * uPR * (uScale / depth);
    gl_Position = projectionMatrix * mv;
  }
`;
const PULSE_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vA;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5 || vA < 0.01) discard;
    float g = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(vColor * g, g * g * vA);
  }
`;

interface Pulse {
  f: number; // fiber index
  fwd: boolean;
  t0: number;
  dur: number;
  kind: 0 | 1 | 2; // idle / ambient / thought
  arrived: boolean;
  col: THREE.Color;
}
export interface LabelBus {
  items: { pos: [number, number, number]; text: string; color: string; born: number; kind: 'thought' | 'sprout' }[];
}

function Pulses({
  model,
  uniforms,
  now,
  stimulus,
  bus,
  onThought,
}: {
  model: Model;
  uniforms: Uniforms;
  now: () => number;
  stimulus: Stimulus | null;
  bus: LabelBus;
  onThought: (steps: ThoughtStep[]) => void;
}) {
  const N = PULSES * TRAIL;
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aColor', new THREE.BufferAttribute(new Float32Array(N * 3), 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSize', new THREE.BufferAttribute(new Float32Array(N), 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aAlpha', new THREE.BufferAttribute(new Float32Array(N), 1).setUsage(THREE.DynamicDrawUsage));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 200);
    return g;
  }, [N]);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: { uPR: uniforms.uPR, uScale: uniforms.uScale },
        vertexShader: PULSE_VERT,
        fragmentShader: PULSE_FRAG,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    [uniforms],
  );
  useEffect(
    () => () => {
      geometry.dispose();
      material.dispose();
    },
    [geometry, material],
  );

  const sim = useRef({
    pulses: Array.from({ length: PULSES }, (): Pulse => ({ f: -1, fwd: true, t0: 0, dur: 1, kind: 0, arrived: true, col: new THREE.Color() })),
    chain: [] as number[],
    chainSet: new Set<number>(),
    chainIds: [] as string[], // neuron index → id for the model the chain was built on
    nextChainAt: 0,
    model: null as Model | null, // the model the sim state belongs to (set by the reset effect)
  });
  const onThoughtRef = useRef(onThought);
  onThoughtRef.current = onThought;

  const ignite = (i: number, amt: number) => {
    model.fire[i] = Math.min(1.8, Math.max(model.fire[i], amt));
    model.fireActive.add(i);
  };
  const pickFiber = (node: number, avoid: Set<number> | null): number => {
    const list = model.adj[node];
    if (!list || list.length === 0) return -1;
    let best = -1;
    let bestScore = -1;
    for (let k = 0; k < Math.min(list.length, 24); k++) {
      const fi = list[k];
      const fb = model.fibers[fi];
      const other = fb.a === node ? fb.b : fb.a;
      if (avoid && (avoid.has(other) || !model.concept[other])) continue;
      const sc = fb.s * (0.4 + Math.random());
      if (sc > bestScore) {
        bestScore = sc;
        best = fi;
      }
    }
    return best;
  };
  const launch = (p: Pulse, fi: number, from: number, kind: 1 | 2, t: number, delay = 0) => {
    const fb = model.fibers[fi];
    p.f = fi;
    p.fwd = fb.a === from;
    p.t0 = t + delay;
    p.dur = Math.max(0.35, fb.len / (kind === 2 ? 15 : 10));
    p.kind = kind;
    p.arrived = false;
    if (kind === 2) p.col.copy(GOLD).multiplyScalar(2.6);
    else p.col.copy(ZCOL[model.zone[from]]).multiplyScalar(1.35);
  };
  const report = () => {
    const s = sim.current;
    onThoughtRef.current(
      s.chain.map((i) => ({ id: model.real[i].id, label: model.real[i].label, zone: model.zoneOf[i] })),
    );
  };
  const labelAt = (i: number, kind: 'thought' | 'sprout', t: number) => {
    bus.items.push({
      pos: [model.pos[i * 3], model.pos[i * 3 + 1], model.pos[i * 3 + 2]],
      text: kind === 'sprout' ? `✦ ${model.real[i].label}` : model.real[i].label,
      color: kind === 'thought' ? '#ffd98a' : ZONES[model.zone[i]].color,
      born: t,
      kind,
    });
    if (bus.items.length > 14) bus.items.splice(0, bus.items.length - 14);
  };
  const startChain = (t: number, from?: number) => {
    const s = sim.current;
    let start = from ?? -1;
    if (start < 0) {
      for (let k = 0; k < 40; k++) {
        const i = (Math.random() * model.real.length) | 0;
        if (model.concept[i] && model.adj[i].length > 0 && model.born[i] < t) {
          start = i;
          break;
        }
      }
    }
    if (start < 0) {
      s.nextChainAt = t + 1;
      return;
    }
    s.chain = [start];
    s.chainSet = new Set([start]);
    ignite(start, 1.5);
    labelAt(start, 'thought', t);
    report();
    const fi = pickFiber(start, s.chainSet);
    if (fi < 0) {
      s.chain = [];
      s.pulses[0].kind = 0; // don't let the previous thought pulse arrive "headless"
      s.nextChainAt = t + 1.2;
      return;
    }
    launch(s.pulses[0], fi, start, 2, t, 0.25);
  };

  // a new model invalidates fiber/neuron indices → reset the ambient impulses, but
  // carry the current thought over (remapped by node id) so it isn't cut short
  useEffect(() => {
    const s = sim.current;
    s.model = model; // from now on useFrame may touch this model's indices
    const t = now();
    const prevIds = s.chain.map((i) => s.chainIds[i]).filter((x): x is string => !!x);
    for (const p of s.pulses) {
      p.kind = 0;
      p.f = -1;
      p.t0 = t + Math.random() * 2;
    }
    const mapped = prevIds.map((id) => model.realIdx.get(id)).filter((i): i is number => i !== undefined);
    s.chain = [];
    s.chainSet = new Set();
    s.nextChainAt = t + 0.6;
    if (mapped.length > 0 && mapped.length === prevIds.length && mapped.length < CHAIN_MAX) {
      const last = mapped[mapped.length - 1];
      const chainSet = new Set(mapped);
      const fi = pickFiber(last, chainSet);
      if (fi >= 0) {
        s.chain = mapped;
        s.chainSet = chainSet;
        launch(s.pulses[0], fi, last, 2, t, 0.3);
      }
    }
    s.chainIds = model.real.map((n) => n.id);
    // newly learned (post-intro) neurons announce themselves
    for (const i of model.sprouts.slice(0, 5)) {
      ignite(i, 1.2);
      labelAt(i, 'sprout', Math.max(t, model.born[i]));
    }
  }, [model]); // eslint-disable-line react-hooks/exhaustive-deps

  // asking the brain: the question's words fire and the thought starts from them
  useEffect(() => {
    if (!stimulus) return;
    const t = now();
    const idx = stimulus.ids.map((id) => model.realIdx.get(id)).filter((i): i is number => i !== undefined);
    if (idx.length === 0) return;
    const s = sim.current;
    let slot = 1;
    for (const i of idx) {
      ignite(i, 1.8);
      if (i !== idx[0]) labelAt(i, 'thought', t);
      for (const fi of model.adj[i].slice(0, 6)) {
        if (slot >= s.pulses.length) break;
        launch(s.pulses[slot++], fi, i, 1, t, Math.random() * 0.4);
      }
    }
    startChain(t, idx[0]);
  }, [stimulus]); // eslint-disable-line react-hooks/exhaustive-deps

  const v = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const t = now();
    const s = sim.current;
    // A new model can reach this callback one frame before the reset effect has run;
    // the sim still holds the OLD model's indices then → skip that frame.
    if (s.model !== model) return;
    const P = geometry.getAttribute('position') as THREE.BufferAttribute;
    const C = geometry.getAttribute('aColor') as THREE.BufferAttribute;
    const S = geometry.getAttribute('aSize') as THREE.BufferAttribute;
    const A = geometry.getAttribute('aAlpha') as THREE.BufferAttribute;
    const pa = P.array as Float32Array;
    const ca = C.array as Float32Array;
    const sa = S.array as Float32Array;
    const aa = A.array as Float32Array;
    const nF = model.fibers.length;
    const live = uniforms.uReveal.value > 0.6 && nF > 0;

    if (live && s.chain.length === 0 && t > s.nextChainAt) startChain(t);

    for (let pi = 0; pi < s.pulses.length; pi++) {
      const p = s.pulses[pi];
      // idle ambient pulse → respawn on a random strong fiber
      if (p.kind === 0 && pi > 0 && live && t > p.t0) {
        for (let k = 0; k < 6; k++) {
          const fi = (Math.random() * nF) | 0;
          const fb = model.fibers[fi];
          if (Math.random() < fb.s + 0.15 && model.born[fb.a] < t && model.born[fb.b] < t) {
            launch(p, fi, Math.random() < 0.5 ? fb.a : fb.b, 1, t);
            break;
          }
        }
      }
      let u = p.kind === 0 || p.f < 0 ? -1 : (t - p.t0) / p.dur;
      if (u >= 1 && !p.arrived) {
        p.arrived = true;
        const fb = model.fibers[p.f];
        const to = p.fwd ? fb.b : fb.a;
        ignite(to, p.kind === 2 ? 1.5 : 0.7);
        if (p.kind === 2) {
          s.chain.push(to);
          s.chainSet.add(to);
          labelAt(to, 'thought', t);
          report();
          const nf = s.chain.length < CHAIN_MAX ? pickFiber(to, s.chainSet) : -1;
          if (nf >= 0) launch(p, nf, to, 2, t, 0.15);
          else {
            p.kind = 0;
            s.chain = [];
            s.nextChainAt = t + 1.8;
          }
        } else if (Math.random() < 0.5) {
          const nf = pickFiber(to, null);
          if (nf >= 0) launch(p, nf, to, 1, t, 0.05);
          else {
            p.kind = 0;
            p.t0 = t + Math.random() * 1.5;
          }
        } else {
          p.kind = 0;
          p.t0 = t + Math.random() * 1.5;
        }
        u = p.kind === 0 ? -1 : (t - p.t0) / p.dur;
      }
      for (let k = 0; k < TRAIL; k++) {
        const o = pi * TRAIL + k;
        const uk = u - k * 0.045;
        if (u < 0 || uk < 0 || uk > 1 || p.f < 0) {
          aa[o] = 0;
          continue;
        }
        const fb = model.fibers[p.f];
        fiberPoint(model.pos, fb, p.fwd ? uk : 1 - uk, v);
        pa[o * 3] = v.x;
        pa[o * 3 + 1] = v.y;
        pa[o * 3 + 2] = v.z;
        const fall = 1 - k / TRAIL;
        ca[o * 3] = p.col.r;
        ca[o * 3 + 1] = p.col.g;
        ca[o * 3 + 2] = p.col.b;
        sa[o] = (p.kind === 2 ? 11 : 6.5) * (0.35 + 0.65 * fall);
        aa[o] = (p.kind === 2 ? 1 : 0.7) * fall * fall;
      }
    }
    P.needsUpdate = true;
    C.needsUpdate = true;
    S.needsUpdate = true;
    A.needsUpdate = true;
  });

  return <points geometry={geometry} material={material} renderOrder={7} raycast={() => null} frustumCulled={false} />;
}

// ════════════════════════════════════════════════════════════════════════════
//  LABELS INSIDE THE BRAIN (DOM overlay, projected every frame)
// ════════════════════════════════════════════════════════════════════════════
const LABEL_ZONES = ZONES.filter((z) => z.id !== 'proto');

function Overlay({
  model,
  counts,
  bus,
  uniforms,
  now,
  focusZone,
  onZoneClick,
}: {
  model: Model;
  counts: Record<ZoneId, number>;
  bus: LabelBus;
  uniforms: Uniforms;
  now: () => number;
  focusZone: ZoneId | null;
  onZoneClick: (z: ZoneId) => void;
}) {
  const { gl, camera } = useThree();
  const dom = useRef<{
    root: HTMLDivElement;
    zones: { z: ZoneId; el: HTMLDivElement; meta: HTMLSpanElement }[];
    concepts: HTMLDivElement[];
    thoughts: HTMLDivElement[];
  } | null>(null);
  const clickRef = useRef(onZoneClick);
  clickRef.current = onZoneClick;

  useEffect(() => {
    const host = gl.domElement.parentElement?.parentElement ?? gl.domElement.parentElement;
    if (!host) return;
    const root = document.createElement('div');
    root.className = 'bx3-ov';
    const zones = LABEL_ZONES.map((z) => {
      const el = document.createElement('div');
      el.className = 'bx3-zl';
      el.style.setProperty('--zc', z.color);
      el.innerHTML = `<span class="bx3-zl-name"><i></i>${z.name}</span>`;
      const meta = document.createElement('span');
      meta.className = 'bx3-zl-meta';
      el.appendChild(meta);
      const stop = (e: Event) => e.stopPropagation();
      el.addEventListener('pointerdown', stop);
      el.addEventListener('pointerup', stop);
      el.addEventListener('pointermove', stop); // else R3F raycasts with label-relative offsets
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        clickRef.current(z.id);
      });
      root.appendChild(el);
      return { z: z.id, el, meta };
    });
    const mk = (cls: string, n: number) =>
      Array.from({ length: n }, () => {
        const el = document.createElement('div');
        el.className = cls;
        root.appendChild(el);
        return el;
      });
    dom.current = { root, zones, concepts: mk('bx3-cl', 16), thoughts: mk('bx3-tl', 14) };
    host.appendChild(root);
    return () => {
      root.remove();
      dom.current = null;
    };
  }, [gl]);

  // zone label meta (lobe · neuron count)
  useEffect(() => {
    const d = dom.current;
    if (!d) return;
    for (const zl of d.zones) {
      const def = ZONES[ZONE_INDEX[zl.z]];
      zl.meta.textContent = `${def.lobe} · ${counts[zl.z].toLocaleString()}`;
    }
  }, [counts]);

  // the most important real concepts of each lobe get a quiet permanent label
  const concepts = useMemo(() => {
    const per = new Map<ZoneId, number[]>();
    model.real.forEach((n, i) => {
      if (!model.concept[i] || n.id.startsWith('prog:')) return;
      const z = model.zoneOf[i];
      if (z === 'memory' && n.kind !== 'profile') return;
      const arr = per.get(z) ?? [];
      arr.push(i);
      per.set(z, arr);
    });
    const out: number[] = [];
    for (const [, arr] of per) out.push(...arr.sort((a, b) => model.size[b] - model.size[a]).slice(0, 3));
    return out.slice(0, 16);
  }, [model]);

  const v = useMemo(() => new THREE.Vector3(), []);
  const cam = useMemo(() => new THREE.Vector3(), []);
  useFrame((state) => {
    const d = dom.current;
    if (!d) return;
    const w = state.size.width;
    const h = state.size.height;
    const t = now();
    const reveal = uniforms.uReveal.value;
    const camDist = uniforms.uCamDist.value;
    cam.copy(camera.position);
    camera.updateMatrixWorld(); // project with THIS frame's camera, not last render's
    const place = (el: HTMLElement, x: number, y: number, z: number, op: number, anchor = '-50%, -50%'): void => {
      v.set(x, y, z).project(camera);
      if (v.z > 1 || op < 0.02) {
        // hidden labels must not catch clicks / drags at their stale position
        el.style.opacity = '0';
        el.style.visibility = 'hidden';
        return;
      }
      el.style.visibility = 'visible';
      el.style.transform = `translate(${(((v.x + 1) / 2) * w).toFixed(1)}px, ${(((1 - v.y) / 2) * h).toFixed(1)}px) translate(${anchor})`;
      el.style.opacity = op.toFixed(3);
    };

    for (const zl of d.zones) {
      let best = ZONE_ANCHORS[zl.z][0];
      let bestF = -2;
      for (const a of ZONE_ANCHORS[zl.z]) {
        const dx = cam.x - a.surface[0];
        const dy = cam.y - a.surface[1];
        const dz = cam.z - a.surface[2];
        const L = Math.hypot(dx, dy, dz) || 1;
        const fc = (a.normal[0] * dx + a.normal[1] * dy + a.normal[2] * dz) / L;
        if (fc > bestF) {
          bestF = fc;
          best = a;
        }
      }
      if (!best) continue;
      const facing = zl.z === 'memory' ? 0.6 : Math.max(0, Math.min(1, (bestF + 0.05) / 0.4));
      const focusK = focusZone ? (focusZone === zl.z ? 1.25 : 0.25) : 0.85;
      const empty = counts[zl.z] === 0;
      const op = Math.min(1, facing * focusK * reveal * (empty ? (zl.z === 'memory' ? 0 : 0.45) : 1));
      const off = zl.z === 'memory' ? 0 : 0.6;
      place(
        zl.el,
        best.surface[0] + best.normal[0] * off,
        best.surface[1] + best.normal[1] * off,
        best.surface[2] + best.normal[2] * off,
        op,
      );
      zl.el.classList.toggle('is-focus', focusZone === zl.z);
    }

    d.concepts.forEach((el, k) => {
      const i = concepts[k];
      if (i === undefined || focusZone) {
        el.style.opacity = '0';
        return;
      }
      // key by node ID, not index: indices are reassigned on every model rebuild
      const nodeId = model.real[i].id;
      if (el.dataset.id !== nodeId) {
        el.dataset.id = nodeId;
        el.textContent = model.real[i].label;
        el.style.color = ZONES[model.zone[i]].color;
      }
      const x = model.pos[i * 3];
      const y = model.pos[i * 3 + 1];
      const z = model.pos[i * 3 + 2];
      const depth = Math.hypot(cam.x - x, cam.y - y, cam.z - z);
      const near = 1 - Math.max(0, Math.min(1, (depth - (camDist - 6)) / 12));
      const grown = Math.max(0, Math.min(1, (t - model.born[i]) / 1.2));
      place(el, x, y, z, 0.55 * near * grown);
    });

    // thought / sprout labels: fade in, hold, fade out
    const items = bus.items;
    for (let k = items.length - 1; k >= 0; k--) if (t - items[k].born > 4.2) items.splice(k, 1);
    d.thoughts.forEach((el, k) => {
      const it = items[k];
      if (!it || t < it.born) {
        el.style.opacity = '0';
        return;
      }
      const key = `${it.text}|${it.born}`;
      if (el.dataset.k !== key) {
        el.dataset.k = key;
        el.textContent = it.text;
        el.style.color = it.color;
        el.classList.toggle('is-sprout', it.kind === 'sprout');
      }
      const age = t - it.born;
      const op = Math.min(1, age / 0.25) * (1 - Math.max(0, (age - 2.8) / 1.4));
      place(el, it.pos[0], it.pos[1], it.pos[2], op, '-50%, -135%');
    });
  });

  return null;
}

// ════════════════════════════════════════════════════════════════════════════
//  GROWTH CHAMBER (incubator under the stem) + background
// ════════════════════════════════════════════════════════════════════════════
const MOTE_VERT = /* glsl */ `
  attribute float aOff;
  attribute float aSpeed;
  uniform float uTime;
  uniform float uPR;
  varying float vA;
  void main() {
    float H = 30.0;
    float y = mod(aOff * H + uTime * aSpeed, H);
    vec3 p = vec3(position.x * (1.0 - y / H * 0.55), ${f(PLATFORM_Y)} + y, position.z * (1.0 - y / H * 0.55));
    float fr = y / H;
    vA = sin(3.14159 * fr) * 0.32;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_PointSize = 1.6 * uPR * (60.0 / max(0.5, -mv.z));
    gl_Position = projectionMatrix * mv;
  }
`;
const MOTE_FRAG = /* glsl */ `
  varying float vA;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    gl_FragColor = vec4(vec3(0.35, 0.85, 1.0), smoothstep(0.5, 0.0, d) * vA);
  }
`;
const DISK_FRAG = /* glsl */ `
  varying vec2 vUv;
  uniform float uTime;
  void main() {
    float r = length(vUv - 0.5) * 2.0;
    float glow = pow(smoothstep(1.0, 0.0, r), 2.0) * 0.07;
    float ring = (1.0 - smoothstep(0.0, 0.012, abs(fract(r * 5.0 - uTime * 0.12) - 0.5) - 0.48)) * smoothstep(1.0, 0.3, r) * 0.035;
    gl_FragColor = vec4(vec3(0.2, 0.75, 0.95), glow + ring);
  }
`;
const DISK_VERT = /* glsl */ `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;

function GrowthChamber({ uniforms }: { uniforms: Uniforms }) {
  const group = useRef<THREE.Group>(null);
  const parts = useMemo(() => {
    const rings = [4.5, 7, 9.5].map((r, k) => {
      const pts: number[] = [];
      const seg = 160;
      for (let i = 0; i < seg; i++) {
        const a0 = (i / seg) * Math.PI * 2;
        const a1 = ((i + 1) / seg) * Math.PI * 2;
        if (k === 1 && i % 8 > 5) continue; // dashed middle ring
        pts.push(Math.cos(a0) * r, 0, Math.sin(a0) * r, Math.cos(a1) * r, 0, Math.sin(a1) * r);
      }
      if (k === 2)
        for (let i = 0; i < 72; i++) {
          const a = (i / 72) * Math.PI * 2;
          const l = i % 6 === 0 ? 1.4 : 0.6;
          pts.push(Math.cos(a) * r, 0, Math.sin(a) * r, Math.cos(a) * (r + l), 0, Math.sin(a) * (r + l));
        }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
      return g;
    });
    // roots: the stem feeding from the chamber
    const roots: number[] = [];
    for (let k = 0; k < 9; k++) {
      const a = (k / 9) * Math.PI * 2 + 0.3;
      const reach = 3 + (k % 3) * 2.2;
      let px = STEM_BOT[0];
      let py = STEM_BOT[1] + 1.5;
      let pz = STEM_BOT[2];
      for (let s = 1; s <= 10; s++) {
        const u = s / 10;
        const nx = STEM_BOT[0] + Math.cos(a) * reach * u * u;
        const ny = STEM_BOT[1] + 1.5 - (STEM_BOT[1] + 1.5 - PLATFORM_Y) * Math.sqrt(u);
        const nz = STEM_BOT[2] + Math.sin(a) * reach * u * u;
        roots.push(px, py, pz, nx, ny, nz);
        px = nx;
        py = ny;
        pz = nz;
      }
    }
    const rootG = new THREE.BufferGeometry();
    rootG.setAttribute('position', new THREE.Float32BufferAttribute(roots, 3));
    // nutrient motes rising toward the brain
    const M = 420;
    const mp = new Float32Array(M * 3);
    const off = new Float32Array(M);
    const spd = new Float32Array(M);
    for (let i = 0; i < M; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 1.2 + Math.sqrt(Math.random()) * 8.5;
      mp[i * 3] = Math.cos(a) * r;
      mp[i * 3 + 2] = Math.sin(a) * r + STEM_BOT[2] * 0.5;
      off[i] = Math.random();
      spd[i] = 0.5 + Math.random() * 0.9;
    }
    const moteG = new THREE.BufferGeometry();
    moteG.setAttribute('position', new THREE.BufferAttribute(mp, 3));
    moteG.setAttribute('aOff', new THREE.BufferAttribute(off, 1));
    moteG.setAttribute('aSpeed', new THREE.BufferAttribute(spd, 1));
    moteG.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 60);
    const moteM = new THREE.ShaderMaterial({
      uniforms: { uTime: uniforms.uTime, uPR: uniforms.uPR },
      vertexShader: MOTE_VERT,
      fragmentShader: MOTE_FRAG,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const diskM = new THREE.ShaderMaterial({
      uniforms: { uTime: uniforms.uTime },
      vertexShader: DISK_VERT,
      fragmentShader: DISK_FRAG,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    return { rings, rootG, moteG, moteM, diskM };
  }, [uniforms]);
  useEffect(
    () => () => {
      parts.rings.forEach((g) => g.dispose());
      parts.rootG.dispose();
      parts.moteG.dispose();
      parts.moteM.dispose();
      parts.diskM.dispose();
    },
    [parts],
  );
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.04;
  });
  return (
    <group>
      <group ref={group} position={[0, PLATFORM_Y, STEM_BOT[2] * 0.5]}>
        {parts.rings.map((g, k) => (
          <lineSegments key={k} geometry={g} raycast={() => null}>
            <lineBasicMaterial color="#2fd8ff" transparent opacity={[0.09, 0.06, 0.045][k]} depthWrite={false} />
          </lineSegments>
        ))}
      </group>
      <mesh position={[0, PLATFORM_Y - 0.02, STEM_BOT[2] * 0.5]} rotation={[-Math.PI / 2, 0, 0]} material={parts.diskM} raycast={() => null}>
        <planeGeometry args={[22, 22]} />
      </mesh>
      <lineSegments geometry={parts.rootG} raycast={() => null}>
        <lineBasicMaterial color="#5fd8ff" transparent opacity={0.13} depthWrite={false} />
      </lineSegments>
      <points geometry={parts.moteG} material={parts.moteM} raycast={() => null} />
    </group>
  );
}

function Stars() {
  const geometry = useMemo(() => {
    const n = 1400;
    const arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 160 + Math.random() * 120;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(ph) * Math.cos(th);
      arr[i * 3 + 1] = r * Math.cos(ph);
      arr[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    return g;
  }, []);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <points geometry={geometry} raycast={() => null}>
      <pointsMaterial size={0.9} color="#8fb4d8" transparent opacity={0.35} sizeAttenuation depthWrite={false} />
    </points>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//  DIRECTOR — uniforms, intro dolly, fly-to, MRI-style scan sweep
// ════════════════════════════════════════════════════════════════════════════
function Animator({ uniforms, now, introStart, reduced }: { uniforms: Uniforms; now: () => number; introStart: { current: number }; reduced: boolean }) {
  const { gl } = useThree();
  useFrame((state) => {
    const t = now();
    uniforms.uTime.value = t;
    uniforms.uPR.value = gl.getPixelRatio();
    uniforms.uCamDist.value = state.camera.position.distanceTo(CENTER_V);
    const since = t - introStart.current;
    uniforms.uReveal.value = reduced ? 1 : Math.min(1, Math.max(0, (since - 0.1) / 2.6));
    const period = 14;
    const phase = ((since - 5) % period) / 3.6;
    uniforms.uScanY.value = !reduced && since > 5 && phase < 1 ? PLATFORM_Y + phase * 31 : -999;
  });
  return null;
}

function CameraDirector({
  controls,
  focus,
  growKey,
  reduced,
}: {
  controls: { current: any };
  focus: FocusTarget | null;
  growKey: number;
  reduced: boolean;
}) {
  const { camera, size } = useThree();
  const st = useRef({ intro: 0, user: false, flyUntil: 0 });
  const tmp = useMemo(() => ({ p: new THREE.Vector3(), d: new THREE.Vector3() }), []);
  // portrait screens need more distance so the whole brain fits the narrow width
  const home = Math.max(HOME_DIST, 46 / Math.max(0.3, size.width / Math.max(1, size.height)));
  const homeRef = useRef(home);
  homeRef.current = home;

  useEffect(() => {
    const h = homeRef.current;
    camera.position.copy(CAM_TARGET).addScaledVector(HOME_DIR, reduced ? h : h * (INTRO_DIST / HOME_DIST));
    st.current.intro = 0;
    st.current.user = false;
    const c = controls.current;
    if (c) {
      c.target.copy(CAM_TARGET);
      c.update();
    }
  }, [growKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    const on = () => {
      st.current.user = true;
      st.current.flyUntil = 0;
    };
    c.addEventListener('start', on);
    return () => c.removeEventListener('start', on);
  }, [controls]);

  useEffect(() => {
    if (focus) {
      st.current.flyUntil = performance.now() + 1900;
      st.current.intro = 6; // a fly-to ends the intro dolly (it would pull the camera back out)
    }
  }, [focus?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  useFrame((_, dt) => {
    const c = controls.current;
    if (!c) return;
    const s = st.current;
    if (focus && performance.now() < s.flyUntil) {
      tmp.p.set(...focus.point);
      tmp.d.copy(tmp.p).sub(CENTER_V);
      if (tmp.d.lengthSq() < 16) tmp.d.copy(HOME_DIR);
      tmp.d.normalize().multiplyScalar(focus.kind === 'zone' ? 32 : 22).add(tmp.p);
      camera.position.lerp(tmp.d, 0.06);
      c.target.lerp(tmp.p, 0.08);
      c.update();
      return;
    }
    if (!focus && c.target.distanceToSquared(CAM_TARGET) > 0.01) {
      c.target.lerp(CAM_TARGET, 0.04);
      c.update();
    }
    if (!s.user && s.intro < 6) {
      s.intro += dt;
      const off = tmp.d.copy(camera.position).sub(c.target);
      const dist = off.length();
      off.setLength(dist + (homeRef.current - dist) * Math.min(1, dt * 0.9));
      camera.position.copy(c.target).add(off);
    }
  });
  return null;
}

function SelectionMarker({ model, selectedId }: { model: Model; selectedId: string | null }) {
  const ref = useRef<THREE.Mesh>(null);
  const { camera } = useThree();
  useFrame((state) => {
    if (!ref.current) return;
    ref.current.quaternion.copy(camera.quaternion);
    ref.current.scale.setScalar(1 + 0.15 * Math.sin(state.clock.elapsedTime * 4));
  });
  const i = selectedId ? model.realIdx.get(selectedId) : undefined;
  if (i === undefined) return null;
  return (
    <mesh ref={ref} position={[model.pos[i * 3], model.pos[i * 3 + 1], model.pos[i * 3 + 2]]} renderOrder={8} raycast={() => null}>
      <ringGeometry args={[0.55, 0.68, 40]} />
      <meshBasicMaterial color={GOLD.clone().multiplyScalar(2)} transparent opacity={0.9} depthWrite={false} toneMapped={false} />
    </mesh>
  );
}

// ════════════════════════════════════════════════════════════════════════════
interface SceneProps {
  graph: BrainGraph;
  layout: BrainLayout;
  selectedId: string | null;
  focus: FocusTarget | null;
  focusZone: ZoneId | null;
  highlightIds: Set<string> | null;
  stimulus: Stimulus | null;
  showProto: boolean;
  growKey: number;
  reducedMotion: boolean;
  onHover: (n: BrainNode | null, x: number, y: number) => void;
  onSelect: (n: BrainNode | null) => void;
  onThought: (steps: ThoughtStep[]) => void;
  onZoneClick: (z: ZoneId) => void;
}

function SceneContent(props: SceneProps) {
  const { graph, layout, selectedId, focus, focusZone, highlightIds, stimulus, showProto, growKey, reducedMotion } = props;
  const controls = useRef<any>(null);
  const t0 = useRef(performance.now() / 1000);
  const now = useMemo(() => () => performance.now() / 1000 - t0.current, []);
  const introStart = useRef(0);
  const births = useRef(new Map<string, number>());
  const lastGrow = useRef(growKey);
  const bus = useMemo<LabelBus>(() => ({ items: [] }), []);

  const uniforms = useMemo<Uniforms>(
    () => ({
      uTime: { value: 0 },
      uPR: { value: 1 },
      uScale: { value: 60 },
      uFocusZone: { value: -1 },
      uScanY: { value: -999 },
      uCamDist: { value: HOME_DIST },
      uReveal: { value: reducedMotion ? 1 : 0 },
    }),
    [], // eslint-disable-line react-hooks/exhaustive-deps
  );
  useEffect(() => {
    uniforms.uFocusZone.value = focusZone ? ZONE_INDEX[focusZone] : -1;
  }, [focusZone, uniforms]);

  const model = useMemo(() => {
    if (lastGrow.current !== growKey) {
      lastGrow.current = growKey;
      births.current.clear();
      introStart.current = now();
      bus.items.length = 0;
    }
    return buildModel(graph, layout, births.current, now(), introStart.current, reducedMotion);
  }, [graph, layout, growKey, reducedMotion, now, bus]);

  return (
    <>
      <color attach="background" args={['#03060c']} />
      <Animator uniforms={uniforms} now={now} introStart={introStart} reduced={reducedMotion} />
      <Stars />
      <GrowthChamber uniforms={uniforms} />
      <Fibers model={model} uniforms={uniforms} />
      <SelectedFibers model={model} uniforms={uniforms} selectedId={selectedId} />
      <ProtoNeurons model={model} uniforms={uniforms} visible={showProto} />
      <Neurons model={model} uniforms={uniforms} highlightIds={highlightIds} onHover={props.onHover} onSelect={props.onSelect} />
      <BrainShell uniforms={uniforms} />
      {!reducedMotion && (
        <Pulses model={model} uniforms={uniforms} now={now} stimulus={stimulus} bus={bus} onThought={props.onThought} />
      )}
      <SelectionMarker model={model} selectedId={selectedId} />
      <Overlay
        model={model}
        counts={layout.counts}
        bus={bus}
        uniforms={uniforms}
        now={now}
        focusZone={focusZone}
        onZoneClick={props.onZoneClick}
      />
      <CameraDirector controls={controls} focus={focus} growKey={growKey} reduced={reducedMotion} />
      <OrbitControls
        ref={controls}
        enablePan={false}
        autoRotate={!reducedMotion && !selectedId}
        autoRotateSpeed={0.28}
        enableDamping
        dampingFactor={0.07}
        minDistance={6}
        maxDistance={120}
      />
      <EffectComposer>
        <Bloom mipmapBlur intensity={0.8} luminanceThreshold={0.72} luminanceSmoothing={0.2} radius={0.7} />
        <Vignette eskil={false} offset={0.22} darkness={0.72} />
      </EffectComposer>
    </>
  );
}

export default function BrainScene(props: SceneProps) {
  return (
    <Canvas
      camera={{ position: [-60, 26, 52], fov: 42, near: 0.5, far: 700 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      raycaster={{ params: { Points: { threshold: 0.32 } } as any }}
      onPointerMissed={() => props.onSelect(null)}
    >
      <SceneContent {...props} />
    </Canvas>
  );
}
