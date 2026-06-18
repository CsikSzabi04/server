// circuitBreaker.ts — search resilience. If the keyless search starts failing
// (DDG blocking / network down), trip the breaker for a cooldown so we stop
// hammering a dead endpoint and fall back gracefully; it auto-recovers (half-open
// probe after the cooldown). localStorage-backed, never throws.
const KEY = 'auri.autolearn.breaker';
const FAIL_THRESHOLD = 3; // consecutive failures to open the circuit
const COOLDOWN_MS = 60_000; // stay open this long, then allow a probe

interface State {
  fails: number;
  openedAt: number;
}

function read(): State {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { fails: 0, openedAt: 0 };
    return JSON.parse(raw) as State;
  } catch {
    return { fails: 0, openedAt: 0 };
  }
}

function write(s: State): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* storage blocked */
  }
}

/** Is a search allowed right now? false while the breaker is open (in cooldown). */
export function searchAllowed(): boolean {
  const s = read();
  return !(s.openedAt && Date.now() - s.openedAt < COOLDOWN_MS);
}

/** Record a search outcome (ok = the request itself succeeded). Drives the breaker. */
export function recordSearchOutcome(ok: boolean): void {
  if (ok) {
    write({ fails: 0, openedAt: 0 }); // success → reset + close
    return;
  }
  const s = read();
  const fails = s.fails + 1;
  write({ fails, openedAt: fails >= FAIL_THRESHOLD ? Date.now() : s.openedAt });
}

/** Wrap a search fn: skip while open, otherwise record the outcome automatically. */
export async function withBreaker<T>(search: () => Promise<T[]>): Promise<T[]> {
  if (!searchAllowed()) return [];
  try {
    const r = await search();
    recordSearchOutcome(true); // the call itself worked
    return r;
  } catch {
    recordSearchOutcome(false);
    return [];
  }
}
