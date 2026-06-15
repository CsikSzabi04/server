import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, type MutableRefObject } from 'react';
import * as THREE from 'three';
import { isSmallScreen } from '../lib/webgl';
import type { AuriState } from '../lib/auriState';

// NOTE: deliberately NO post-processing bloom. UnrealBloom was the main GPU cost
// AND caused the white-out (HDR colors + low threshold saturating to white).
// Instead the "glow" comes from controlled additive layers with colors kept
// <= 1, so the centre stays golden and the whole scene is much cheaper.
// The 3D core is also frame-capped (~30fps) to keep CPU/GPU usage low.

interface Params {
  color: THREE.Color;
  speed: number;
  glow: number; // halo/sprite strength
  core: number;
  inflow: number;
  glitch: number;
}
type ParamsRef = MutableRefObject<Params>;

// Saturated ambers with a LOW blue channel: no matter how many additive layers
// stack, the result can never climb to white (blue stays low) — it just gets a
// more intense orange-gold.
const STATE_COLOR: Record<AuriState, THREE.Color> = {
  idle: new THREE.Color(0xff8c1a),
  listening: new THREE.Color(0xffa430),
  thinking: new THREE.Color(0xffb238),
  speaking: new THREE.Color(0xffa82e),
  error: new THREE.Color(0xff3a28),
};

interface Target {
  speed: number;
  glow: number;
  core: number;
  inflow: number;
  glitch: number;
}
function targetFor(state: AuriState): Target {
  switch (state) {
    case 'listening':
      return { speed: 1.5, glow: 0.55, core: 1.05, inflow: 0.15, glitch: 0 };
    case 'thinking':
      return { speed: 2.4, glow: 0.8, core: 1.2, inflow: 1, glitch: 0 };
    case 'speaking':
      return { speed: 1.7, glow: 0.7, core: 1.12, inflow: 0.3, glitch: 0 };
    case 'error':
      return { speed: 0.7, glow: 0.6, core: 0.95, inflow: 0, glitch: 1 };
    case 'idle':
    default:
      return { speed: 1, glow: 0.45, core: 1, inflow: 0, glitch: 0 };
  }
}

function fibonacciSphere(n: number, radius: number) {
  const positions = new Float32Array(n * 3);
  const phases = new Float32Array(n);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / Math.max(1, n - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i;
    const j = 0.04;
    positions[i * 3] = (Math.cos(theta) * r + (Math.random() - 0.5) * j) * radius;
    positions[i * 3 + 1] = (y + (Math.random() - 0.5) * j) * radius;
    positions[i * 3 + 2] = (Math.sin(theta) * r + (Math.random() - 0.5) * j) * radius;
    phases[i] = Math.random();
  }
  return { positions, phases };
}

function randDir(): THREE.Vector3 {
  const v = new THREE.Vector3(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1);
  if (v.lengthSq() < 1e-4) v.set(1, 0, 0);
  return v.normalize();
}
function makeCurves(count: number, radius: number): THREE.CatmullRomCurve3[] {
  const curves: THREE.CatmullRomCurve3[] = [];
  for (let i = 0; i < count; i++) {
    const segs = 3 + Math.floor(Math.random() * 2);
    const start = randDir();
    const end = randDir();
    const pts: THREE.Vector3[] = [];
    for (let s = 0; s <= segs; s++) {
      pts.push(start.clone().lerp(end, s / segs).normalize().multiplyScalar(radius * (0.9 + Math.random() * 0.18)));
    }
    curves.push(new THREE.CatmullRomCurve3(pts));
  }
  return curves;
}

function makeGlowTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,140,35,0.55)');
  g.addColorStop(0.4, 'rgba(255,110,20,0.22)');
  g.addColorStop(1, 'rgba(255,90,10,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

const SHELL_VERT = /* glsl */ `
  uniform float uTime;
  uniform float uSize;
  uniform float uContract;
  attribute float aPhase;
  varying float vTw;
  varying float vDepth;
  void main() {
    float tw = 0.55 + 0.45 * sin(uTime * 2.2 + aPhase * 6.2831);
    vTw = tw;
    float contract = 1.0 - uContract * 0.12 * (0.5 + 0.5 * sin(uTime * 1.5 + aPhase * 6.0));
    vec3 p = position * contract;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float dist = max(0.001, -mv.z);
    vDepth = clamp((dist - 2.2) / 2.4, 0.0, 1.0); // 0 = front, 1 = back
    // small, few-pixel points, gently attenuated by distance (NOT 300px discs!)
    gl_PointSize = uSize * (0.7 + 0.6 * tw) * (3.0 / dist);
    gl_Position = projectionMatrix * mv;
  }
`;
const SHELL_FRAG = /* glsl */ `
  precision mediump float;
  uniform vec3 uColor;
  uniform float uAlpha;
  varying float vTw;
  varying float vDepth;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float d = length(c);
    if (d > 0.5) discard;
    float a = smoothstep(0.5, 0.0, d);
    float depthFade = 1.0 - vDepth * 0.7; // back hemisphere dimmer -> real depth
    gl_FragColor = vec4(uColor * (0.65 + 0.5 * vTw), a * uAlpha * depthFade);
  }
`;

const approach = (cur: number, target: number, dt: number) => cur + (target - cur) * Math.min(1, dt * 3);

// Frame-rate limiter: render on demand at ~targetFps to roughly halve GPU/CPU.
function FpsLimiter({ fps }: { fps: number }) {
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    const id = window.setInterval(() => invalidate(), 1000 / fps);
    return () => window.clearInterval(id);
  }, [invalidate, fps]);
  return null;
}

function ParticleShell({ params, count }: { params: ParamsRef; count: number }) {
  const points = useRef<THREE.Points>(null);
  const { positions, phases } = useMemo(() => fibonacciSphere(count, 1), [count]);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor: { value: new THREE.Color(0xff9d2f) },
      uSize: { value: 2.3 },
      uAlpha: { value: 0.55 },
      uContract: { value: 0 },
    }),
    [],
  );

  useFrame(({ clock }, dt) => {
    uniforms.uTime.value = clock.elapsedTime;
    uniforms.uColor.value.lerp(params.current.color, Math.min(1, dt * 3));
    uniforms.uAlpha.value = 0.5 * params.current.core;
    uniforms.uContract.value = params.current.inflow;
    if (points.current) {
      points.current.rotation.y += dt * 0.2 * params.current.speed;
      points.current.rotation.x += dt * 0.05;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-aPhase" args={[phases, 1]} />
      </bufferGeometry>
      <shaderMaterial
        args={[
          {
            uniforms,
            vertexShader: SHELL_VERT,
            fragmentShader: SHELL_FRAG,
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
          },
        ]}
      />
    </points>
  );
}

function HotCore({ params }: { params: ParamsRef }) {
  const core = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(({ clock }) => {
    const pulse = 1 + 0.1 * Math.sin(clock.elapsedTime * 2);
    core.current?.scale.setScalar(0.2 * params.current.core * pulse);
    // core uses the SAME saturated amber as everything else — never white
    if (mat.current) mat.current.color.copy(params.current.color);
  });
  return (
    <mesh ref={core}>
      <icosahedronGeometry args={[1, 2]} />
      <meshBasicMaterial ref={mat} transparent opacity={0.45} toneMapped={false} depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  );
}

function EnergyLines({ params, curves }: { params: ParamsRef; curves: THREE.CatmullRomCurve3[] }) {
  const group = useRef<THREE.Group>(null);
  const mats = useRef<THREE.MeshBasicMaterial[]>([]);
  const flash = useRef<number[]>(curves.map(() => 0));
  useFrame((_, dt) => {
    if (group.current) {
      group.current.rotation.y -= dt * 0.06 * params.current.speed;
      group.current.rotation.x += dt * 0.02 * params.current.speed;
    }
    for (let i = 0; i < curves.length; i++) {
      if (flash.current[i] > 0) flash.current[i] -= dt * 2.2;
      else if (Math.random() < 0.004 * params.current.speed) flash.current[i] = 1;
      const m = mats.current[i];
      if (m) {
        m.opacity = 0.12 + Math.max(0, flash.current[i]) * 0.7;
        m.color.copy(params.current.color);
      }
    }
  });
  return (
    <group ref={group}>
      {curves.map((curve, i) => (
        <mesh key={i}>
          <tubeGeometry args={[curve, 22, 0.005, 4, false]} />
          <meshBasicMaterial
            ref={(el) => {
              if (el) mats.current[i] = el;
            }}
            transparent
            opacity={0.08}
            depthWrite={false}
            toneMapped={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  );
}

function Sparks({ params, curves }: { params: ParamsRef; curves: THREE.CatmullRomCurve3[] }) {
  const N = 6;
  const ref = useRef<THREE.Points>(null);
  const matRef = useRef<THREE.PointsMaterial>(null);
  const positions = useMemo(() => new Float32Array(N * 3).fill(999), []);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const sparks = useRef(
    Array.from({ length: N }, () => ({
      ci: Math.floor(Math.random() * curves.length),
      t: Math.random(),
      spd: 0.5 + Math.random() * 0.8,
      delay: Math.random() * 2.5,
    })),
  );
  useFrame((_, dt) => {
    for (let i = 0; i < N; i++) {
      const s = sparks.current[i];
      if (s.delay > 0) {
        s.delay -= dt;
        positions[i * 3] = 999;
        continue;
      }
      s.t += dt * s.spd * (0.6 + params.current.speed * 0.4);
      if (s.t >= 1) {
        s.t = 0;
        s.ci = Math.floor(Math.random() * curves.length);
        s.delay = Math.random() * 2.5;
      }
      curves[s.ci].getPoint(Math.min(0.999, Math.max(0, s.t)), tmp);
      positions[i * 3] = tmp.x;
      positions[i * 3 + 1] = tmp.y;
      positions[i * 3 + 2] = tmp.z;
    }
    const geo = ref.current?.geometry;
    if (geo) (geo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    if (matRef.current) matRef.current.color.copy(params.current.color);
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial ref={matRef} size={0.075} sizeAttenuation transparent depthWrite={false} toneMapped={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}

function Rings3D({ params }: { params: ParamsRef }) {
  const group = useRef<THREE.Group>(null);
  const mats = useRef<THREE.MeshBasicMaterial[]>([]);
  const rings: { r: number; tube: number; rot: [number, number, number] }[] = [
    { r: 1.45, tube: 0.006, rot: [Math.PI / 2.2, 0, 0.3] },
    { r: 1.62, tube: 0.005, rot: [0.4, 0.6, 0] },
  ];
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.1 * params.current.speed;
    for (const m of mats.current) if (m) m.color.copy(params.current.color);
  });
  return (
    <group ref={group}>
      {rings.map((rr, i) => (
        <mesh key={i} rotation={rr.rot}>
          <torusGeometry args={[rr.r, rr.tube, 6, 80]} />
          <meshBasicMaterial
            ref={(el) => {
              if (el) mats.current[i] = el;
            }}
            transparent
            opacity={0.4}
            depthWrite={false}
            toneMapped={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  );
}

function GlowHalo({ params }: { params: ParamsRef }) {
  const sprite = useRef<THREE.Sprite>(null);
  const mat = useRef<THREE.SpriteMaterial>(null);
  const tex = useMemo(() => makeGlowTexture(), []);
  useFrame(({ clock }) => {
    const s = 1.4 * (1 + 0.05 * Math.sin(clock.elapsedTime * 0.8));
    sprite.current?.scale.set(s, s, 1);
    if (mat.current) {
      mat.current.color.copy(params.current.color);
      mat.current.opacity = 0.1 + params.current.glow * 0.12;
    }
  });
  return (
    <sprite ref={sprite}>
      <spriteMaterial ref={mat} map={tex} transparent depthWrite={false} toneMapped={false} blending={THREE.AdditiveBlending} />
    </sprite>
  );
}

function Dust() {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const N = 40;
    const a = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      a[i * 3] = (Math.random() - 0.5) * 6;
      a[i * 3 + 1] = (Math.random() - 0.5) * 5;
      a[i * 3 + 2] = (Math.random() - 0.5) * 4 - 1;
    }
    return a;
  }, []);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.01;
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.02} color="#ffcf6e" transparent opacity={0.35} sizeAttenuation depthWrite={false} toneMapped={false} blending={THREE.AdditiveBlending} />
    </points>
  );
}

function CameraRig() {
  const { camera } = useThree();
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    camera.position.x = Math.sin(t * 0.25) * 0.2;
    camera.position.y = Math.sin(t * 0.2) * 0.14;
    camera.position.z = 3.3 + Math.sin(t * 0.3) * 0.14;
    camera.lookAt(0, 0, 0);
  });
  return null;
}

function Scene({ state, particles, lines }: { state: AuriState; particles: number; lines: number }) {
  const params = useRef<Params>({ color: new THREE.Color(0xff9d2f), speed: 1, glow: 0.45, core: 1, inflow: 0, glitch: 0 });
  const curves = useMemo(() => makeCurves(lines, 1.16), [lines]);
  const assembly = useRef<THREE.Group>(null);

  useFrame((_, dt) => {
    const t = targetFor(state);
    const p = params.current;
    p.color.lerp(STATE_COLOR[state], Math.min(1, dt * 3));
    p.speed = approach(p.speed, t.speed, dt);
    p.glow = approach(p.glow, t.glow, dt);
    p.core = approach(p.core, t.core, dt);
    p.inflow = approach(p.inflow, t.inflow, dt);
    p.glitch = approach(p.glitch, t.glitch, dt);
    if (assembly.current) {
      assembly.current.rotation.y += dt * 0.15 * p.speed;
      assembly.current.rotation.z = Math.sin(performance.now() * 0.0002) * 0.12;
      if (p.glitch > 0.02) {
        assembly.current.position.set((Math.random() - 0.5) * p.glitch * 0.2, (Math.random() - 0.5) * p.glitch * 0.2, 0);
      } else {
        assembly.current.position.set(0, 0, 0);
      }
    }
  });

  return (
    <>
      <FpsLimiter fps={30} />
      <CameraRig />
      <GlowHalo params={params} />
      <group ref={assembly}>
        <ParticleShell params={params} count={particles} />
        <HotCore params={params} />
      </group>
      <EnergyLines params={params} curves={curves} />
      <Sparks params={params} curves={curves} />
      <Rings3D params={params} />
      <Dust />
    </>
  );
}

export default function MindCore3D({ state }: { state: AuriState }) {
  const small = isSmallScreen();
  const particles = small ? 1500 : 3800;
  const lines = small ? 6 : 10;

  return (
    <Canvas
      className="mindcore-canvas"
      frameloop="demand"
      dpr={[1, 1]}
      gl={{ alpha: false, antialias: false, powerPreference: 'high-performance', stencil: false, depth: true }}
      camera={{ position: [0, 0, 3.3], fov: 50 }}
      onCreated={({ gl }) => gl.setClearColor(0x05080f, 1)}
    >
      <Scene state={state} particles={particles} lines={lines} />
    </Canvas>
  );
}
