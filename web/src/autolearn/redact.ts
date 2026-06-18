// redact.ts — strip obvious PII from a query BEFORE it leaves the device for web
// search. The personal layer (facts/profile) never goes to the search provider;
// only a cleaned query does. Pure string work, never throws.

const EMAIL = /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g;
const PHONE = /(?:\+?\d[\s-]?){7,}/g; // 7+ digit runs → phone-ish
const LONGNUM = /\b\d{6,}\b/g; // long digit sequences (ids, cards, etc.)

export interface RedactOptions {
  /** Extra terms to strip, e.g. the user's name/nickname from their profile. */
  names?: string[];
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function redactForSearch(query: string, opts: RedactOptions = {}): string {
  let q = query.replace(EMAIL, ' ').replace(PHONE, ' ').replace(LONGNUM, ' ');
  for (const name of opts.names ?? []) {
    const n = name.trim();
    if (n.length > 1) q = q.replace(new RegExp(`\\b${escapeRegExp(n)}\\b`, 'gi'), ' ');
  }
  return q.replace(/\s+/g, ' ').trim();
}
