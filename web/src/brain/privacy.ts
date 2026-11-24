// privacy.ts — keeps PERSONAL data out of the BRAIN.
//
// Rule: the brain (the learner's vocabulary, associations and Q→A recall) holds only
// general / technical knowledge. Personal data — birth dates, addresses, contacts,
// names, IDs, passwords, workplace/school self-disclosures — never goes into it.
// Personal facts belong ONLY to the signed-in user's own account memory (Supabase,
// Row Level Security); a logged-out session sees none of it (see lib/memStore.ts).
//
// Pure string checks, no imports, never throws. Errs on the side of "personal":
// a false positive only means one chat turn is not learned.

const PERSONAL: RegExp[] = [
  /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/, // e-mail
  // phone numbers: "+36 30 123 4567", "06 30 123 4567", "06/30/123-4567", "555-123-4567".
  // Must start with +country or a 0X trunk prefix — a bare run of spaced digits is too often
  // code or CSS ("rgb(59 130 246 / 50%)", "1 2 3 4 5 6 7 8"). Unbroken 6+ digit runs are
  // caught by the ID rule below anyway.
  /(?:\+\d{1,3}|\b0\d)[\s/-]?(?:\d[\s/-]?){7,}/,
  /\b\d{3}[-.]\d{3}[-.]\d{4}\b/,
  /\b\d{6,}\b/, // ID / card / account numbers
  // full dates — birthdays etc. ("2004. január 23.", "2004-01-23", "23/01/2004")
  // Needs a DAY too: "2025. novemberi kiadás" / "2024. decemberben jelent meg" are release
  // dates — programming knowledge the brain must keep learning — not birthdays.
  /\b(19|20)\d{2}\s*[.\-/]\s*(0?[1-9]|1[0-2]|január|február|március|április|május|június|július|augusztus|szeptember|október|november|december)\s*[.\-/]?\s*(0?[1-9]|[12]\d|3[01])\b/i,
  /\b(0?[1-9]|[12]\d|3[01])[./](0?[1-9]|1[0-2])[./](19|20)\d{2}\b/,
  // Hungarian self-disclosure / personal records
  /\b(szület\w*|szülinap\w*|lakcím\w*|lakom|lakunk|lakik|címem|telefonszám\w*|személyi(?!ség)\w*|adóazonosító\w*|adószám\w*|taj-?szám\w*|bankkártya\w*|számlaszám\w*|jelszav\w*|jelszó\w*)/i,
  /\b(a nevem|nevem|hívnak engem|éves vagyok|munkahelyem|egyetemre járok|egyetemen tanulok|hallgató vagyok)\b/i,
  /\b\S+(nak|nek) hívnak\b/i, // "Alexnek hívnak"
  // "Szegeden élek" — place + "élek" (I live). A bare "élek" is NOT enough: it also means
  // graph edges ("csúcsok és élek"), which programming knowledge must keep learning.
  /\S{3,}(ban|ben|on|en|ön) (élek|élünk)\b/i,
  // English self-disclosure / personal records
  /\b(my name is|i am called|i was born|born (on|in)|my birthday|i live (in|at)|my address|my phone|phone number|my password|password is|social security|credit card|i study at|i work at|years old)\b/i,
];

// The CURRENT identity's own names (profile name + nickname, and each part of them),
// registered by the memory layer (hooks/useMemory.ts) whenever the profile loads or
// changes. Every isPersonal() call checks them, so "írj portfóliót rólam, Teszt Elek"
// is blocked on EVERY learning path (observe, distill, recall, Code Projects…), not
// only where a caller remembered to pass the names.
let ownNames: RegExp[] = [];

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** lower-case + accents removed: "Máté" and a typed "Mate" match the same way. */
const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
// Hungarian endings after a name (folded): Eleknek, Eleket, Elekkel, Elekről, Szabinak,
// Eleké… — a name INSIDE another word ("elektron" for Elek) is not a match.
const NAME_SUFFIX = '(?:nak|nek|[a-z]?(?:al|el)|ert|rol|rul|ra|re|ba|be|ban|ben|hoz|hez|tol|tul|nal|nel|ig|kent|bol|bul|ek|e|[aeou]?[tnks])?';

/** Matchers for a list of names: "Teszt Elek" → "teszt elek", "teszt", "elek" (each
 *  part ≥ 3 letters), as whole words with an optional Hungarian ending. */
function nameMatchers(names: (string | null | undefined)[]): RegExp[] {
  const out = new Set<string>();
  for (const raw of names) {
    const n = fold(raw ?? '').trim().replace(/\s+/g, ' ');
    if (n.length < 3) continue;
    out.add(n);
    for (const part of n.split(/[\s,()/.-]+/)) if (part.length >= 3) out.add(part);
  }
  return [...out].map((n) => new RegExp(`(^|[^\\p{L}\\p{N}])${esc(n)}${NAME_SUFFIX}(?![\\p{L}\\p{N}])`, 'u'));
}

/** Register the current identity's own names (call with [] / undefined on logout). */
export function setOwnNames(names: (string | null | undefined)[]): void {
  ownNames = nameMatchers(names);
}

/** Does this text contain personal data that must never be learned by the brain? */
export function isPersonal(text: string, names: string[] = []): boolean {
  if (!text) return false;
  if (PERSONAL.some((re) => re.test(text))) return true;
  if (!ownNames.length && !names.length) return false;
  const t = fold(text);
  if (ownNames.some((re) => re.test(t))) return true;
  return names.length > 0 && nameMatchers(names).some((re) => re.test(t));
}
