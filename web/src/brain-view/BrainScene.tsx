import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import type { BrainGraph, BrainNode, Positions } from './types';
import { isWebNode } from './types';

// Stable 0..1 hash for a node id (palette variety, deterministic across renders).
function hash01(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

// "Plexus brain" palette (BRAIN.md III look): mostly warm copper/amber neurons,
// with a sprinkle of cool cyan/white sparks — like the reference render.
function paletteColor(id: string, out: THREE.Color): THREE.Color {
  const t = hash01(id + 'c');
  if (t < 0.82) {
    // warm: hue 18..40 (orange → amber), varied lightness
    return out.setHSL((18 + (t / 0.82) * 22) / 360, 0.92, 0.42 + 0.2 * hash01(id + 'l'));
  }
  // cool spark: cyan → white
  const w = (t - 0.82) / 0.18; // 0..1
  return out.setHSL(190 / 360, 0.55 * (1 - w), 0.66 + 0.3 * w);
}

// ── nodes: ONE THREE.Points (1 draw call for thousands of neurons) ────────────
// size = importance (weight), color = region; a glow sprite in the fragment shader;
// zoom-based LOD culls low-importance nodes when zoomed out (uLodCut) so the dense
// brain stays readable, then reveals every strand as you fly in.
const NODE_VERT = /* glsl */ `
  attribute vec3 aColor;
  attribute float aSize;
  attribute float aImportance;
  uniform float uTime;
  uniform float uLodCut;
  uniform float uPixelRatio;
  varying vec3 vColor;
  varying float vKeep;
  void main() {
    vColor = aColor;
    float keep = step(uLodCut, aImportance);
    vKeep = keep;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float tw = 0.82 + 0.18 * sin(uTime * 1.6 + aImportance * 53.0);
    gl_PointSize = aSize * tw * keep * uPixelRatio * (9.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
  }
`;
const NODE_FRAG = /* glsl */ `
  varying vec3 vColor;
  varying float vKeep;
  void main() {
    if (vKeep < 0.5) discard;
    vec2 c = gl_PointCoord - 0.5;
    float d = length(c);
    if (d > 0.5) discard;
    float core = smoothstep(0.5, 0.0, d);
    // normal blending: show the node's colour with a soft round alpha (no white sum)
    gl_FragColor = vec4(vColor * (0.65 + 0.5 * core), core * 0.85);
  }
`;

function buildNodeGeometry(graph: BrainGraph, positions: Positions, highlightIds: Set<string> | null): THREE.BufferGeometry {
  const nodes = graph.nodes;
  const N = nodes.length;
  const pos = new Float32Array(N * 3);
  const col = new Float32Array(N * 3);
  const size = new Float32Array(N);
  const imp = new Float32Array(N);
  const maxW = Math.max(1, ...nodes.map((n) => n.weight ?? 1));
  const tmp = new THREE.Color();
  for (let i = 0; i < N; i++) {
    const n = nodes[i];
    const p = positions[n.id] ?? [0, 0, 0];
    pos[i * 3] = p[0];
    pos[i * 3 + 1] = p[1];
    pos[i * 3 + 2] = p[2];
    const importance = n.kind === 'profile' || n.pinned ? 1 : Math.min(1, (n.weight ?? 1) / maxW);
    imp[i] = importance;
    let s = 2.0 + importance * 7 + (n.kind === 'profile' ? 5 : 0);
    paletteColor(n.id, tmp);
    if (isWebNode(n)) {
      tmp.setHSL(320 / 360, 0.85, 0.62); // web-learned knowledge stands out (magenta)
      s += 4;
    }
    let r = tmp.r;
    let g = tmp.g;
    let b = tmp.b;
    if (highlightIds) {
      if (highlightIds.has(n.id)) {
        r = 1;
        g = 0.82;
        b = 0.4;
        s *= 1.5;
      } else {
        r *= 0.16;
        g *= 0.16;
        b *= 0.16;
      }
    }
    size[i] = s;
    col[i * 3] = r;
    col[i * 3 + 1] = g;
    col[i * 3 + 2] = b;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  geo.setAttribute('aImportance', new THREE.BufferAttribute(imp, 1));
  return geo;
}

function Nodes({
  graph,
  positions,
  highlightIds,
  reducedMotion,
  onHover,
  onSelect,
}: {
  graph: BrainGraph;
  positions: Positions;
  highlightIds: Set<string> | null;
  reducedMotion: boolean;
  onHover: (n: BrainNode | null, x: number, y: number) => void;
  onSelect: (n: BrainNode | null) => void;
}) {
  const { gl } = useThree();
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uLodCut: { value: 0 },
          uPixelRatio: { value: gl.getPixelRatio() },
        },
        vertexShader: NODE_VERT,
        fragmentShader: NODE_FRAG,
        transparent: true,
        depthWrite: false,
        // NORMAL blending (not additive): dense overlapping nodes no longer SUM to a
        // white blob — they blend by alpha, so the brain silhouette stays readable.
        blending: THREE.NormalBlending,
      }),
    [gl],
  );
  const geometry = useMemo(() => buildNodeGeometry(graph, positions, highlightIds), [graph, positions, highlightIds]);
  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((state, dt) => {
    if (!reducedMotion) material.uniforms.uTime.value += dt;
    const dist = state.camera.position.length();
    // zoom-based LOD: dense by default; only thin out low-importance nodes once you
    // pull FAR back (readability), and reveal every strand as you fly in.
    material.uniforms.uLodCut.value = Math.min(0.65, Math.max(0, ((dist - 32) / 30) * 0.65));
  });

  return (
    <points
      geometry={geometry}
      material={material}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        if (e.index != null && graph.nodes[e.index])
          onHover(graph.nodes[e.index], e.nativeEvent.clientX, e.nativeEvent.clientY);
      }}
      onPointerOut={() => onHover(null, 0, 0)}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        if (e.index != null && graph.nodes[e.index]) onSelect(graph.nodes[e.index]);
      }}
    />
  );
}

// ── edges: ONE THREE.LineSegments (1 draw call for thousands of synapses) ─────
// color brightness = strength; edges touching the selected node turn gold; overall
// opacity eases with zoom so faint strands don't clutter when zoomed out.
function buildEdgeGeometry(graph: BrainGraph, positions: Positions, selectedId: string | null): THREE.BufferGeometry {
  const pos: number[] = [];
  const col: number[] = [];
  for (const e of graph.edges) {
    const a = positions[e.a];
    const b = positions[e.b];
    if (!a || !b) continue;
    const sel = !!selectedId && (e.a === selectedId || e.b === selectedId);
    let r: number;
    let g: number;
    let bl: number;
    if (sel) {
      r = 1;
      g = 0.82;
      bl = 0.42;
    } else {
      // warm copper strands; the strongest (most-learned) lean white-hot
      const st = e.strength ?? 0.3;
      const k = 0.2 + 0.8 * st;
      r = 1.0 * k;
      g = (0.48 + 0.42 * st) * k;
      bl = (0.2 + 0.6 * st) * k;
    }
    pos.push(a[0], a[1], a[2], b[0], b[1], b[2]);
    col.push(r, g, bl, r, g, bl);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  return geo;
}

function Edges({ graph, positions, selectedId }: { graph: BrainGraph; positions: Positions; selectedId: string | null }) {
  const geometry = useMemo(() => buildEdgeGeometry(graph, positions, selectedId), [graph, positions, selectedId]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  const matRef = useRef<THREE.LineBasicMaterial>(null);
  useFrame((state) => {
    if (!matRef.current) return;
    const dist = state.camera.position.length();
    matRef.current.opacity = THREE.MathUtils.lerp(0.12, 0.04, Math.min(1, Math.max(0, (dist - 12) / 44)));
  });
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial
        ref={matRef}
        vertexColors
        transparent
        opacity={0.2}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        toneMapped={false}
      />
    </lineSegments>
  );
}

// A gold marker on the selected neuron (single cheap mesh).
function SelectionMarker({ positions, selectedId }: { positions: Positions; selectedId: string | null }) {
  if (!selectedId) return null;
  const p = positions[selectedId];
  if (!p) return null;
  return (
    <mesh position={p}>
      <sphereGeometry args={[0.22, 16, 16]} />
      <meshBasicMaterial color="#ffd166" toneMapped={false} />
    </mesh>
  );
}

// Faint drifting dust around the brain — depth + a sense of "life".
function Particles({ count = 1500 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 11 + Math.random() * 20;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      arr[i * 3 + 1] = r * Math.cos(phi) * 0.8;
      arr[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }
    g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    return g;
  }, [count]);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.01;
  });
  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial size={0.05} color="#7fd8ff" transparent opacity={0.28} sizeAttenuation depthWrite={false} toneMapped={false} />
    </points>
  );
}

// Smoothly flies the camera to the focused node.
function CameraRig({ focus, controls }: { focus: [number, number, number] | null; controls: { current: any } }) {
  const { camera } = useThree();
  const desired = useRef(new THREE.Vector3());
  const targetV = useRef(new THREE.Vector3());
  useFrame(() => {
    if (!focus) return;
    desired.current.set(focus[0], focus[1], focus[2] + 7);
    camera.position.lerp(desired.current, 0.05);
    if (controls.current?.target) {
      targetV.current.set(focus[0], focus[1], focus[2]);
      controls.current.target.lerp(targetV.current, 0.07);
      controls.current.update();
    }
  });
  return null;
}

// Golden synapse-flash when the brain just learned something from the WEB
// (a new region:web / URL-sourced node appears). Fixed mesh pool + ref-driven
// animation (no per-frame React state) → cheap and robust. Skips the very first
// build (so the existing brain doesn't all flash at once on load).
const FLASH_POOL = 14;
function WebFlash({ graph, positions }: { graph: BrainGraph; positions: Positions }) {
  const seen = useRef<Set<string>>(new Set());
  const initialized = useRef(false);
  const pulses = useRef<{ pos: THREE.Vector3; born: number }[]>([]);
  const meshes = useRef<(THREE.Mesh | null)[]>([]);

  useEffect(() => {
    const now = performance.now() / 1000;
    if (!initialized.current) {
      for (const n of graph.nodes) seen.current.add(n.id);
      initialized.current = true;
      return;
    }
    for (const n of graph.nodes) {
      if (seen.current.has(n.id)) continue;
      seen.current.add(n.id);
      if (!isWebNode(n)) continue;
      const p = positions[n.id];
      if (p) pulses.current.push({ pos: new THREE.Vector3(p[0], p[1], p[2]), born: now });
    }
    if (pulses.current.length > FLASH_POOL) pulses.current.splice(0, pulses.current.length - FLASH_POOL);
  }, [graph, positions]);

  const DUR = 1.3;
  useFrame(() => {
    const now = performance.now() / 1000;
    pulses.current = pulses.current.filter((p) => now - p.born < DUR);
    for (let i = 0; i < FLASH_POOL; i++) {
      const m = meshes.current[i];
      if (!m) continue;
      const p = pulses.current[i];
      if (!p) {
        m.visible = false;
        continue;
      }
      const age = (now - p.born) / DUR; // 0..1
      m.visible = true;
      m.position.copy(p.pos);
      m.scale.setScalar(0.25 + age * 1.7);
      (m.material as THREE.MeshBasicMaterial).opacity = (1 - age) * 0.9;
    }
  });

  return (
    <>
      {Array.from({ length: FLASH_POOL }).map((_, i) => (
        <mesh
          key={i}
          ref={(el: THREE.Mesh | null) => {
            meshes.current[i] = el;
          }}
          visible={false}
        >
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial
            color="#ffd166"
            transparent
            opacity={0}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            toneMapped={false}
          />
        </mesh>
      ))}
    </>
  );
}

interface SceneProps {
  graph: BrainGraph;
  positions: Positions;
  selectedId: string | null;
  focus: [number, number, number] | null;
  highlightIds: Set<string> | null;
  reducedMotion: boolean;
  onHover: (n: BrainNode | null, x: number, y: number) => void;
  onSelect: (n: BrainNode | null) => void;
}

export default function BrainScene({
  graph,
  positions,
  selectedId,
  focus,
  highlightIds,
  reducedMotion,
  onHover,
  onSelect,
}: SceneProps) {
  const controls = useRef<any>(null);

  return (
    <Canvas
      camera={{ position: [36, 3, 0], fov: 50 }}
      dpr={[1, 2]}
      raycaster={{ params: { Points: { threshold: 0.28 } } as any }}
      onPointerMissed={() => onSelect(null)}
    >
      <color attach="background" args={['#04080f']} />
      <fog attach="fog" args={['#04080f', 38, 92]} />
      {!reducedMotion && <Particles />}
      <Edges graph={graph} positions={positions} selectedId={selectedId} />
      <Nodes
        graph={graph}
        positions={positions}
        highlightIds={highlightIds}
        reducedMotion={reducedMotion}
        onHover={onHover}
        onSelect={onSelect}
      />
      <SelectionMarker positions={positions} selectedId={selectedId} />
      {!reducedMotion && <WebFlash graph={graph} positions={positions} />}
      <CameraRig focus={focus} controls={controls} />
      <OrbitControls
        ref={controls}
        enablePan={false}
        autoRotate={!reducedMotion}
        autoRotateSpeed={0.3}
        enableDamping
        dampingFactor={0.08}
        minDistance={2}
        maxDistance={80}
      />
      <EffectComposer>
        <Bloom mipmapBlur intensity={0.9} luminanceThreshold={0.35} luminanceSmoothing={0.25} />
      </EffectComposer>
    </Canvas>
  );
}
