// lang.ts — lightweight language detection for the literal brain (brain/** zone;
// the existing memory.ts detectLanguage stays untouched). Distinguishes the three
// languages the brain is seeded with, used to pick the answer language and for the
// /brain stage readout.
export type Lang = 'hu' | 'en' | 'de' | 'unknown';

const HU_FUNC =
  /\b(a|az|és|nem|hogy|vagyok|te|én|ő|mi|ti|ők|igen|köszönöm|szia|van|nincs|mit|hol|miért|kérlek|jó)\b/g;
const DE_FUNC = /\b(der|die|das|und|nicht|ich|ist|ein|eine|mit|auch|wie|was|ja|nein|danke|hallo|du|wir|sie|sehr)\b/g;
const EN_FUNC = /\b(the|and|not|is|are|a|an|i|you|we|they|yes|no|thanks|hello|what|where|why|please|have)\b/g;

const count = (t: string, re: RegExp): number => t.match(re)?.length ?? 0;

/** Best-effort language guess: 'hu' | 'en' | 'de' | 'unknown'. */
export function detectLang(text: string): Lang {
  const t = text.toLowerCase();
  if (!/[a-zäöüßáéíóúőű]/.test(t)) return 'unknown';

  // Hungarian-unique accents (German has none of á é í ó ú ő ű)
  if (/[őűáéíóú]/.test(t)) return 'hu';
  // German-unique marks
  if (/[äß]/.test(t)) return 'de';

  // function-word voting (handles plain ASCII + ö/ü ambiguity)
  const hu = count(t, HU_FUNC);
  const de = count(t, DE_FUNC);
  const en = count(t, EN_FUNC);
  // Strict '>' so a tie (e.g. the ambiguous lone article "a", which is both Hungarian
  // and English) falls through to English — the safe default for accent-less ASCII.
  if (hu > 0 && hu > de && hu > en) return 'hu';
  if (de > 0 && de > en) return 'de';
  if (en > 0) return 'en';

  // ö/ü with no other signal leans German (Hungarian-unique accents already matched)
  if (/[öü]/.test(t)) return 'de';
  return 'en';
}
