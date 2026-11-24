// techAlias.ts — tiny shared helpers so tech names with symbols ("C#", "C++", ".NET")
// and very short names ("C", "Go") can be matched safely by the BRAIN's finders
// (findKnowledge, findSnippet, findSource). The word tokenizers keep only [a-z0-9],
// so "c#" / "c++" would otherwise vanish and ".net" would become a bare "net".
//
// Rules: matching is always at a WORD START (never buried inside another word —
// "trust" must not mean Rust, "agy" must not hit "vagy"); one-letter names must be a
// whole word; short names take at most a 3-letter suffix; long names may take any
// suffix (Hungarian inflection: "pythonban", "linuxon", "reactot").

/** Rewrite symbol/short tech names into plain word tokens the finders can match. */
export function expandTechAliases(text: string): string {
  return text
    .replace(/(^|[^a-z0-9])c#/gi, '$1 csharp ')
    .replace(/(^|[^a-z0-9])c\+\+/gi, '$1 cpp ')
    .replace(/(^|[^a-z0-9])f#/gi, '$1 fsharp ')
    .replace(/(^|[a-z0-9]*)\.net\b/gi, (_m, pre: string) => `${pre} dotnet `)
    .replace(/(^|[^a-z0-9])go(?=\s*(-?nyelv|-?ban|-?ben|-?val|-?ul|\s+language|\s+lang\b|\s+programming|\s+programoz))/gi, '$1golang')
    .replace(/(^|[^a-z0-9])in go\s*[?.!]*\s*$/gi, '$1in golang')
    .replace(/[ \t]{2,}/g, ' ');
}

/** Lowercase + alias-expand + strip diacritics (accent-insensitive matching). */
export function normalizeTechQuery(text: string): string {
  return expandTechAliases(text.toLowerCase())
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

const isWordChar = (c: string | undefined): boolean => c !== undefined && /[a-z0-9]/.test(c);

/** Does the (already normalized) query mention this tech id as a word? */
export function mentionsTech(q: string, tech: string): boolean {
  for (let i = q.indexOf(tech); i >= 0; i = q.indexOf(tech, i + 1)) {
    if (isWordChar(q[i - 1])) continue; // buried mid-word ("trust" ≠ "rust")
    let rest = 0;
    while (isWordChar(q[i + tech.length + rest])) rest++;
    const maxSuffix = tech.length === 1 ? 0 : tech.length < 4 ? 3 : Infinity;
    if (rest <= maxSuffix) return true;
  }
  return false;
}
