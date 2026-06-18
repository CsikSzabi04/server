// trust.ts — domain authority (0..1) + freshness (TTL) heuristics for web results,
// so the loop prefers authoritative sources and re-fetches volatile facts when stale.

const HIGH = [
  'developer.mozilla.org', 'nodejs.org', 'react.dev', 'reactjs.org', 'typescriptlang.org',
  'w3.org', 'whatwg.org', 'python.org', 'docs.python.org', 'rust-lang.org', 'go.dev', 'golang.org',
  'developer.apple.com', 'developer.android.com', 'learn.microsoft.com', 'docs.microsoft.com',
  'kubernetes.io', 'postgresql.org', 'sqlite.org', 'tailwindcss.com', 'getbootstrap.com',
  'developer.chrome.com', 'web.dev', 'rfc-editor.org', 'ietf.org',
];
const MED = [
  'wikipedia.org', 'stackoverflow.com', 'github.com', 'gitlab.com', 'npmjs.com',
  'freecodecamp.org', 'css-tricks.com', 'smashingmagazine.com', 'digitalocean.com', 'baeldung.com',
];

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase();
  } catch {
    return '';
  }
}

/** Domain authority for a result URL: 1 official docs, 0.65 known good, 0.4 unknown. */
export function domainTrust(url: string): number {
  const host = hostOf(url);
  if (!host) return 0.3;
  if (HIGH.some((d) => host === d || host.endsWith('.' + d))) return 1;
  if (MED.some((d) => host === d || host.endsWith('.' + d))) return 0.65;
  return 0.4;
}

// ── Freshness ────────────────────────────────────────────────────────────────
const VOLATILE = /\b(price|cost|ár|árak|news|hír|today|latest|legújabb|2024|2025|2026|version|verzió|release)\b/i;

/** Suggested time-to-live (days) for a web-derived fact, by topic volatility. */
export function ttlDaysForQuery(query: string): number {
  return VOLATILE.test(query) ? 3 : 180;
}

/** Has a web-derived memory gone stale? `fetchedAt` is an ISO timestamp. */
export function isStale(fetchedAt: string, ttlDays: number): boolean {
  const t = Date.parse(fetchedAt);
  if (Number.isNaN(t)) return true;
  return Date.now() - t > ttlDays * 86_400_000;
}
