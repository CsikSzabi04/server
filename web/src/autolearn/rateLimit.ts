// rateLimit.ts — a tiny token-bucket limiter (localStorage-backed) so the keyless
// web search isn't hammered under heavy use (avoids slowdowns / being blocked).
// Refills `capacity` tokens continuously over `windowMs`. Never throws.

export interface RateLimitOptions {
  /** Bucket name (namespaced in localStorage). */
  key?: string;
  /** Max requests allowed per window. */
  capacity?: number;
  /** Window length (ms) over which the bucket fully refills. */
  windowMs?: number;
}

interface Bucket {
  tokens: number;
  updatedAt: number;
}

const PREFIX = 'auri.autolearn.rl.';
const DEFAULT_CAPACITY = 12; // 12 searches…
const DEFAULT_WINDOW_MS = 60_000; // …per minute

function read(key: string, capacity: number): Bucket {
  try {
    const b = JSON.parse(localStorage.getItem(PREFIX + key) || 'null') as Bucket | null;
    return b ?? { tokens: capacity, updatedAt: Date.now() };
  } catch {
    return { tokens: capacity, updatedAt: Date.now() };
  }
}

function write(key: string, b: Bucket): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(b));
  } catch {
    /* storage blocked */
  }
}

function refilled(b: Bucket, capacity: number, windowMs: number, now: number): number {
  return Math.min(capacity, b.tokens + ((now - b.updatedAt) / windowMs) * capacity);
}

/**
 * Try to consume one token. Returns true if allowed (and consumes it), false if
 * the bucket is empty — the caller should then skip the web search and fall back.
 */
export function allowRequest(opts: RateLimitOptions = {}): boolean {
  const key = opts.key ?? 'search';
  const capacity = opts.capacity ?? DEFAULT_CAPACITY;
  const windowMs = opts.windowMs ?? DEFAULT_WINDOW_MS;
  const now = Date.now();
  const tokens = refilled(read(key, capacity), capacity, windowMs, now);
  if (tokens < 1) {
    write(key, { tokens, updatedAt: now });
    return false;
  }
  write(key, { tokens: tokens - 1, updatedAt: now });
  return true;
}

/** Tokens currently available (fractional) — handy for a UI hint. */
export function availableTokens(opts: RateLimitOptions = {}): number {
  const key = opts.key ?? 'search';
  const capacity = opts.capacity ?? DEFAULT_CAPACITY;
  const windowMs = opts.windowMs ?? DEFAULT_WINDOW_MS;
  return refilled(read(key, capacity), capacity, windowMs, Date.now());
}
