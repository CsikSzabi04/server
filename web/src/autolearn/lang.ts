// lang.ts — minimal, self-contained language hint (accent-based, like
// memory.detectLanguage). Kept local so this lane does not depend on AI-1's
// brain/lang.ts. Cautious by design: only strong accent signals classify.
import type { Lang } from './types';

export function detectLang(text: string): Lang {
  const t = text.toLowerCase();
  // Hungarian-unique accents (ő/ű/á/é/í/ó/ú) — not present in German.
  if (/[őűáéíóú]/.test(t)) return 'hu';
  // German-unique letters.
  if (/[äöüß]/.test(t)) return 'de';
  if (/[a-z]/.test(t)) return 'en';
  return 'unknown';
}
