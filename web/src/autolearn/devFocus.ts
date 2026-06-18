// devFocus.ts — bias the web-learning loop toward PROGRAMMING: detect technical
// queries, prefer developer / official-docs / code sources, and expand queries
// toward code & documentation. Makes the knowledge the brain learns (and its web
// answers) programmer-oriented. Pure, no deps; layers on top of rerank/trust.
import { extractKeywords } from '../lib/memory';
import { domainTrust } from './trust';
import type { Hit, ScoredHit } from './types';

const DEV_DOMAINS = [
  'stackoverflow.com', 'stackexchange.com', 'github.com', 'gitlab.com', 'developer.mozilla.org',
  'devdocs.io', 'npmjs.com', 'pypi.org', 'crates.io', 'pkg.go.dev', 'docs.python.org', 'nodejs.org',
  'react.dev', 'vuejs.org', 'angular.io', 'typescriptlang.org', 'rust-lang.org', 'go.dev',
  'learn.microsoft.com', 'docs.oracle.com', 'baeldung.com', 'geeksforgeeks.org', 'freecodecamp.org',
  'css-tricks.com', 'web.dev', 'developer.chrome.com', 'digitalocean.com', 'dev.to',
];

const PROG_TERMS =
  /\b(code|coding|program|programming|function|class|method|api|sdk|library|framework|compile|runtime|debug|error|exception|stack ?trace|install|npm|pip|cargo|git|deploy|docker|kubernetes|database|sql|query|endpoint|async|await|promise|component|hook|css|html|javascript|typescript|python|java|rust|golang|react|vue|angular|node|regex|algorithm|array|object|json|http|rest|graphql|frontend|backend|fullstack|függvény|osztály|metódus|kód|programoz|hiba|fordít|telepít|adatbázis|lekérdezés)\b/i;

const CODE_HINT = /[{}();=>]|```|\bfunction\b|\bconst\b|\bimport\b|\bclass\b|<\/?[a-z]+>/i;

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase();
  } catch {
    return '';
  }
}

/** Does this query look like a programming / developer question? */
export function isProgrammingQuery(query: string): boolean {
  return PROG_TERMS.test(query);
}

/** Extra authority for dev / official-docs / code sources (1 if dev domain, else 0). */
export function devTrust(url: string): number {
  const host = hostOf(url);
  if (!host) return 0;
  return DEV_DOMAINS.some((d) => host === d || host.endsWith('.' + d)) ? 1 : 0;
}

/**
 * Rerank hits with a PROGRAMMING bias: base overlap × domain-trust, PLUS a boost
 * for dev domains and code-bearing snippets, so developer sources surface first.
 * Use when isProgrammingQuery(query) — or always, for a dev-focused assistant.
 */
export function rerankDev<T extends Hit>(query: string, hits: T[], top = 6): T[] {
  const qk = new Set(extractKeywords(query, 12));
  return hits
    .map((hit): ScoredHit<T> => {
      let overlap = 0;
      for (const k of extractKeywords(`${hit.title} ${hit.snippet}`, 16)) if (qk.has(k)) overlap++;
      const trust = domainTrust(hit.url);
      const dev = devTrust(hit.url);
      const code = CODE_HINT.test(hit.snippet) ? 1 : 0;
      const score = overlap * 5 + trust * 4 + dev * 6 + code * 3; // dev + code push programming sources up
      return { hit, score, trust, overlap };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, top)
    .map((s) => s.hit);
}

/** Programming-oriented search variants (docs, code examples, Q&A). */
export function expandDev(query: string): string[] {
  const core = extractKeywords(query, 8).join(' ') || query.trim();
  return [core, `${core} code example`, `${core} documentation`, `${core} stackoverflow`];
}
