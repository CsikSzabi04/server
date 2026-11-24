// stem.ts — a light, bilingual (Hungarian + English) stemmer used to MATCH inflected
// forms to one concept ("fut/futok/futás" → "fut", "running/runs" → "run"). It is
// deliberately conservative: it folds accents, strips at most two common suffixes,
// and never cuts below a 3-letter stem — so it helps recall without mangling words.
// Used for MATCHING only (recall, coverage); the stored vocabulary keeps raw words,
// so the 3D graph stays dense.

// Common suffixes, folded (accent-free). Longest are tried first (sorted below).
const SUFFIXES: string[] = [
  // Hungarian — derivation
  'asok', 'esek', 'ozas', 'ezes', 'as', 'es',
  // Hungarian — case / possessive / plural
  'aibol', 'eibol', 'oknak', 'eknek', 'aknak',
  'ban', 'ben', 'bol', 'bel', 'rol', 'rel', 'nak', 'nek', 'val', 'vel',
  'hoz', 'hez', 'hoz', 'tol', 'tel', 'nal', 'nel', 'kent', 'ert', 'ig', 'ul',
  'unk', 'tok', 'tek', 'juk', 'juk',
  'ak', 'ek', 'ok', 'at', 'et', 'ot', 'ba', 'be', 'ra', 're', 'on', 'en', 'ja', 'je',
  't', 'k', 'i',
  // English
  'ingly', 'edly', 'ing', 'ied', 'ies', 'ment', 'ness', 'tion', 'sion',
  'ers', 'er', 'est', 'ly', 'ed', 'es', 's',
];
const ORDERED = [...new Set(SUFFIXES)].sort((a, b) => b.length - a.length);

const MIN_STEM = 3;
// A one-letter suffix ('k', 't', 'i', 's') is too ambiguous to strip from a 4-letter word:
// "fork" → "for" collided with "forest" → "for", "book"/"boot" → "boo". Keep ≥ 4 letters.
const MIN_STEM_SHORT_SUFFIX = 4;

/** Lowercase + strip accents (the raw, unstemmed form used for exact-word checks). */
export function foldWord(word: string): string {
  return word.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** Reduce a word to a matching key: accent-folded, up to two suffixes stripped. */
export function stemKey(word: string): string {
  let w = foldWord(word);
  if (w.length <= 3) return w;
  for (let pass = 0; pass < 2; pass++) {
    let cut = false;
    for (const suf of ORDERED) {
      const min = suf.length === 1 ? MIN_STEM_SHORT_SUFFIX : MIN_STEM;
      if (w.length - suf.length >= min && w.endsWith(suf)) {
        w = w.slice(0, -suf.length);
        cut = true;
        break;
      }
    }
    if (!cut || w.length <= 4) break;
  }
  return w;
}

/** Stem a set of keywords into a deduped set of stems. */
export function stemSet(words: Iterable<string>): Set<string> {
  const out = new Set<string>();
  for (const w of words) out.add(stemKey(w));
  return out;
}
