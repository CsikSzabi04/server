// types.ts — structural, dependency-free types for the autolearn lane.
// Deliberately does NOT import brain-bridge's WebHit, so this lane stays decoupled
// from the AIs' files: any object shaped { title, url, snippet } works, and
// brain-bridge's WebHit is structurally compatible with Hit.

export interface Hit {
  title: string;
  url: string;
  snippet: string;
}

export type Lang = 'hu' | 'en' | 'de' | 'unknown';

export interface ScoredHit<T extends Hit = Hit> {
  hit: T;
  score: number; // final rank score (overlap × 5 + trust × 4)
  trust: number; // 0..1 domain authority
  overlap: number; // count of query keywords found in title+snippet
}
