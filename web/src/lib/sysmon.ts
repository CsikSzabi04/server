// Real, machine-dependent telemetry pulled from standard browser APIs.
//
// IMPORTANT (privacy / "can this be public?"): every value here is read CLIENT-SIDE
// in the visitor's own browser and only displayed back to them — nothing is sent
// to any server. The only network call is a same-origin ping to our own favicon
// to measure round-trip latency. So yes, this is safe to ship publicly. Some
// metrics are Chromium-only (JS heap, deviceMemory, connection) and degrade
// gracefully to "—" elsewhere. Geolocation is deliberately NOT used (it would
// need a permission prompt); we show the timezone instead.

export interface SysStatic {
  cores: number; // logical CPU cores
  memGB: number; // approx device RAM (Chromium), 0 if unknown
  dpr: number; // device pixel ratio
  screen: string; // "1920×1080"
  gpu: string; // WebGL renderer (may be masked)
  secure: boolean; // HTTPS / localhost
  timezone: string;
  language: string;
}

export interface SysLive {
  fps: number;
  loadPct: number; // render load estimate from FPS vs. the device's own max
  memPct: number | null; // JS heap used % (Chromium)
  memUsedMB: number | null;
  latencyMs: number | null; // same-origin ping RTT
  online: boolean;
  netType: string; // 'effective' connection type, or 'n/a'
  downlink: number | null; // Mbps (Chromium)
  battery: number | null; // 0..100
  charging: boolean | null;
}

const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));

function detectGpu(): string {
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl') || c.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    if (!gl) return 'no-webgl';
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    const raw = dbg ? (gl.getParameter((dbg as any).UNMASKED_RENDERER_WEBGL) as string) : '';
    if (!raw) return 'hidden';
    // strip the "ANGLE (Vendor, Renderer Direct3D...)" wrapper down to the core name
    const m = raw.match(/ANGLE \(([^,]+),\s*([^,]+)/);
    return (m ? m[2] : raw).replace(/\s*\(.*$/, '').trim().slice(0, 28);
  } catch {
    return 'unknown';
  }
}

export const SYS_STATIC: SysStatic = {
  cores: navigator.hardwareConcurrency || 0,
  memGB: (navigator as any).deviceMemory || 0,
  dpr: Math.round((window.devicePixelRatio || 1) * 100) / 100,
  screen: `${window.screen.width}×${window.screen.height}`,
  gpu: detectGpu(),
  secure: window.isSecureContext === true,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'n/a',
  language: navigator.language || 'n/a',
};

// ── live sampling singleton (one rAF loop + one poll, shared by all consumers) ─
let live: SysLive = {
  fps: 0,
  loadPct: 0,
  memPct: null,
  memUsedMB: null,
  latencyMs: null,
  online: navigator.onLine,
  netType: 'n/a',
  downlink: null,
  battery: null,
  charging: null,
};

const listeners = new Set<(s: SysLive) => void>();
const emit = () => {
  for (const fn of listeners) fn(live);
};

let started = false;
let fps = 0;
let frames = 0;
let lastFpsAt = performance.now();
let maxFps = 60;
let battery: any = null;

function fpsLoop(now: number) {
  frames++;
  const dt = now - lastFpsAt;
  if (dt >= 500) {
    fps = Math.round((frames * 1000) / dt);
    frames = 0;
    lastFpsAt = now;
    if (fps > maxFps) maxFps = Math.min(fps, 240); // learn the display's real refresh
  }
  requestAnimationFrame(fpsLoop);
}

function readMem(): { pct: number | null; usedMB: number | null } {
  const pm = (performance as any).memory;
  if (pm && pm.jsHeapSizeLimit) {
    return {
      pct: Math.round((pm.usedJSHeapSize / pm.jsHeapSizeLimit) * 100),
      usedMB: Math.round(pm.usedJSHeapSize / 1048576),
    };
  }
  return { pct: null, usedMB: null };
}

async function ping(): Promise<number | null> {
  const t0 = performance.now();
  try {
    await fetch(`/favicon.svg?t=${Date.now()}`, { cache: 'no-store' });
    return Math.round(performance.now() - t0);
  } catch {
    return null;
  }
}

async function tick() {
  const mem = readMem();
  const conn = (navigator as any).connection;
  const latency = await ping();
  live = {
    fps,
    loadPct: clamp(Math.round((1 - fps / Math.max(1, maxFps)) * 100), 0, 99),
    memPct: mem.pct,
    memUsedMB: mem.usedMB,
    latencyMs: latency,
    online: navigator.onLine,
    netType: conn?.effectiveType ?? 'n/a',
    downlink: typeof conn?.downlink === 'number' ? conn.downlink : null,
    battery: battery ? Math.round(battery.level * 100) : null,
    charging: battery ? battery.charging : null,
  };
  emit();
}

function ensureStarted() {
  if (started) return;
  started = true;
  lastFpsAt = performance.now();
  requestAnimationFrame(fpsLoop);
  const navAny = navigator as any;
  if (typeof navAny.getBattery === 'function') {
    navAny
      .getBattery()
      .then((b: any) => {
        battery = b;
      })
      .catch(() => {});
  }
  void tick();
  window.setInterval(() => void tick(), 2000);
}

export function subscribeSys(fn: (s: SysLive) => void): () => void {
  ensureStarted();
  listeners.add(fn);
  fn(live);
  return () => {
    listeners.delete(fn);
  };
}
