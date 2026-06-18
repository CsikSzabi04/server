// bilingual.ts — Hungarian→English query helper. Technical content is often better
// in English, so for a Hungarian query we also build an English-leaning variant by
// mapping common programming/general terms via a small curated dictionary (no model,
// no deps). Pure. Pair with mergeSearches to search both and merge.
import { detectLang } from './lang';

const HU_EN: Record<string, string> = {
  függvény: 'function', osztály: 'class', metódus: 'method', változó: 'variable',
  tömb: 'array', objektum: 'object', ciklus: 'loop', feltétel: 'condition',
  hiba: 'error', kivétel: 'exception', hibakeresés: 'debugging', fordítás: 'compile',
  telepítés: 'install', telepíteni: 'install', csomag: 'package', könyvtár: 'library',
  keretrendszer: 'framework', adatbázis: 'database', lekérdezés: 'query', tábla: 'table',
  kiszolgáló: 'server', kliens: 'client', böngésző: 'browser', hálózat: 'network',
  fájl: 'file', mappa: 'folder', karakterlánc: 'string', szám: 'number',
  visszatérés: 'return', paraméter: 'parameter', argumentum: 'argument',
  öröklődés: 'inheritance', felület: 'interface', esemény: 'event', üzenet: 'message',
  kód: 'code', programozás: 'programming', fejlesztés: 'development', verzió: 'version',
  gyors: 'fast', lassú: 'slow', biztonság: 'security', teljesítmény: 'performance',
  példa: 'example', oktatóanyag: 'tutorial', dokumentáció: 'documentation',
  hogyan: 'how to', miért: 'why',
};

/** Map recognized Hungarian (tech) words to English; leave the rest as-is. */
export function toEnglishish(query: string): string {
  return query
    .toLowerCase()
    .split(/(\s+)/)
    .map((tok) => HU_EN[tok.replace(/[.,!?;:()]/g, '')] ?? tok)
    .join('')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Original + an English-leaning variant (only when it differs and the input is HU). */
export function bilingualQueries(query: string): string[] {
  const base = query.trim();
  const out = [base];
  if (detectLang(query) === 'hu') {
    const en = toEnglishish(query);
    if (en && en !== base.toLowerCase()) out.push(en);
  }
  return out;
}
