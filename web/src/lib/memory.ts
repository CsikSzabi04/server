// The BRAIN engine (pure, local). Extracts keywords / name / facts from a turn,
// and builds the compact "memory context" injected into the system prompt so
// Auri remembers the user and personalises replies. No server logic here — the
// storage layer (memStore) decides where the results live (Supabase / local).

export interface Profile {
  name?: string;
  nickname?: string;
  language?: string;
  tone?: string;
  about?: string;
  interests?: string[];
  prefs?: Record<string, unknown>;
}

export interface Memory {
  id?: string;
  kind: 'fact' | 'keyword' | 'doc' | 'summary';
  content: string;
  weight: number;
  pinned?: boolean;
  source?: string;
  created_at?: string;
}

export const PERSONA =
  'Te Auri vagy, egy gyors és segítőkész AI-asszisztens. Válaszolj magyarul, tömören, ' +
  'barátságosan és lényegre törően. Ha a felhasználó más nyelven ír, azon a nyelven válaszolj.';

// Hungarian + English stop-words (kept compact; good enough for keyword signal).
const STOP = new Set(
  (
    'a az egy és vagy de hogy nem is meg ki be el fel le rá rol ról ben ban nak nek val vel ' +
    'mint csak már még ez az ezt azt itt ott így úgy mert ha majd lesz volt van vannak lenne ' +
    'te én ő mi ti ők enyém tied övé nekem neked neki minden semmi valami nagyon kicsit kérlek ' +
    'the a an and or but that not is are was were be been being to of in on at for with as by ' +
    'this that these those it its from your you i we they he she my me do does did so if then ' +
    'what which who how why when where can will would could should just like about into over'
  ).split(/\s+/),
);

/** Top frequency keywords (3+ letters, unicode-aware so Hungarian works). */
export function extractKeywords(text: string, max = 10): string[] {
  const words = text.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) ?? [];
  const freq = new Map<string, number>();
  for (const w of words) {
    if (STOP.has(w)) continue;
    freq.set(w, (freq.get(w) ?? 0) + 1);
  }
  return [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, max).map(([w]) => w);
}

/** Heuristic name detection ("X vagyok", "hívj X-nek", "my name is X", "call me X"). */
export function detectName(text: string): string | null {
  const patterns: RegExp[] = [
    /(?:a nevem|engem h[ií]vnak|h[ií]vj(?:atok|on)?(?:\s+engem)?)\s+([A-ZÁÉÍÓÖŐÚÜŰ][\p{L}]{1,20})/u,
    /\b([A-ZÁÉÍÓÖŐÚÜŰ][\p{L}]{1,20})\s+vagyok\b/u,
    /(?:my name is|i am|i'm|call me)\s+([A-Z][a-z]{1,20})/i,
  ];
  const BAD = new Set(['fáradt', 'éhes', 'kíváncsi', 'biztos', 'itt', 'jól', 'rosszul']);
  for (const re of patterns) {
    const m = text.match(re);
    if (m && m[1] && !BAD.has(m[1].toLowerCase())) return m[1];
  }
  return null;
}

/** Only sets a language when there's a strong signal (Hungarian accents). */
export function detectLanguage(text: string): string | undefined {
  return /[áéíóöőúüű]/i.test(text) ? 'magyar' : undefined;
}

/** Capture short self-statements as facts (declarative, first-person, not a question). */
function extractFacts(text: string): string[] {
  const t = text.trim();
  if (!t || t.length > 200 || t.endsWith('?')) return [];
  if (
    /\b(én|nekem|enyém|szeretem|utálom|kedvenc|projekt|dolgozom|vagyok|szeretnék|lakom|tanulok|i'm|i am|my |i like|i love|i work|i live|i study|favou?rite)\b/i.test(
      t,
    )
  ) {
    return [t];
  }
  return [];
}

export interface TurnAnalysis {
  keywords: string[];
  name: string | null;
  language?: string;
  facts: string[];
}

export function analyzeTurn(userText: string, assistantText: string): TurnAnalysis {
  return {
    keywords: extractKeywords(`${userText} ${assistantText}`, 10),
    name: detectName(userText),
    language: detectLanguage(userText),
    facts: extractFacts(userText),
  };
}

/** Pick the memories most relevant to the current query (pinned + weight + overlap). */
function relevantMemories(memories: Memory[], query: string, limit = 8): Memory[] {
  const q = new Set(extractKeywords(query, 12));
  return memories
    .map((m) => {
      let score = (m.pinned ? 100 : 0) + (m.weight ?? 1);
      for (const w of extractKeywords(m.content, 12)) if (q.has(w)) score += 5;
      return { m, score };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .filter((x) => x.score > 0)
    .map((x) => x.m);
}

/** Build the full system message: persona + what Auri knows that's relevant now. */
export function buildSystemMessage(profile: Profile, memories: Memory[], query: string): string {
  const parts: string[] = [PERSONA];

  const who: string[] = [];
  if (profile.name) who.push(`neve: ${profile.name}`);
  if (profile.nickname) who.push(`becenév: ${profile.nickname}`);
  if (profile.language) who.push(`nyelv: ${profile.language}`);
  if (profile.tone) who.push(`hangnem: ${profile.tone}`);
  if (profile.interests?.length) who.push(`érdeklődés: ${profile.interests.slice(0, 6).join(', ')}`);
  if (profile.about) who.push(`rólam: ${profile.about}`);
  if (who.length) parts.push(`Amit a felhasználóról tudsz: ${who.join('; ')}.`);

  const rel = relevantMemories(memories, query);
  const facts = rel.filter((m) => m.kind === 'fact' || m.kind === 'doc' || m.kind === 'summary');
  if (facts.length) {
    parts.push('Releváns korábbi infók:\n' + facts.map((m) => `- ${m.content}`).join('\n'));
  }

  if (profile.name) parts.push(`Ha természetes, szólítsd a felhasználót a nevén (${profile.name}).`);
  return parts.join('\n\n');
}
