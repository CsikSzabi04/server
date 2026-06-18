// Grow-in / golden-flash timing for the 3D map. State is per-Canvas-mount (held
// in a useRef, NOT module-level) so it can never go stale across HMR/remounts
// and hide the nodes. On first sync the existing nodes are marked "already
// settled" (instantly full size — no intro flicker); only nodes added LATER
// (new memories) grow in from ~0 and get a golden synapse flash.
export interface AppearState {
  at: Map<string, number>;
  initialized: boolean;
}

export function newAppearState(): AppearState {
  return { at: new Map(), initialized: false };
}

const GROW = 0.7; // seconds: new node scales 0 → full
const FLASH = 0.95; // seconds: golden flash on a new node's strands

export function syncAppear(st: AppearState, ids: string[], now: number): void {
  if (!st.initialized) {
    for (const id of ids) st.at.set(id, -1e9); // already settled → full size now
    st.initialized = true;
    return;
  }
  for (const id of ids) if (!st.at.has(id)) st.at.set(id, now); // new → grow + flash
}

/** 0→1 grow factor (settled nodes return 1; never returns 0 → always visible). */
export function growFactor(st: AppearState, id: string, now: number): number {
  const t0 = st.at.get(id);
  if (t0 == null) return 1;
  const dt = now - t0;
  if (dt >= GROW) return 1; // includes the settled (-1e9) initial batch
  if (dt <= 0) return 0.06; // just spawned this frame
  const p = dt / GROW;
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return Math.max(0.06, 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2);
}

/** 1→0 golden flash for a newly appeared node (0 for settled nodes). */
export function flashFactor(st: AppearState, id: string, now: number): number {
  const t0 = st.at.get(id);
  if (t0 == null) return 0;
  const dt = now - t0;
  return dt >= 0 && dt < FLASH ? 1 - dt / FLASH : 0;
}
