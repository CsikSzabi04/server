// bulkVocab.ts — a procedural generator that gives the brain a LARGE vocabulary
// (the user wants ~1M words: ~70% programming, ~30% general) offline, with no
// external data. It synthesizes realistic tokens from morphemes and emits them in
// short SEQUENCES so the learner also forms word→word links (Stage 4). The curated
// knowledge base (knowledge.ts) still provides the *meaning*; this provides breadth
// and the dense, brain-like graph. Tokens are lowercased (matching tokenize()).

// ── programming morphemes ──────────────────────────────────────────────────────
import { EXTRA_WORDS } from './words.ingested';

const TECH = [
  '', 'js', 'ts', 'node', 'react', 'vue', 'svelte', 'html', 'css', 'sass', 'api', 'db', 'sql', 'http', 'rest', 'app',
  'web', 'core', 'base', 'main', 'dev', 'test', 'async', 'cli', 'ui', 'dom', 'json', 'auth', 'jwt', 'cache', 'redis',
  'mongo', 'postgres', 'docker', 'cloud', 'edge', 'micro', 'mini',
  // the technologies the user asked Auri to "know everything" about + their ecosystems
  'python', 'py', 'java', 'kotlin', 'php', 'phpmyadmin', 'oracle', 'vite', 'mysql', 'mariadb', 'spring', 'django',
  'flask', 'laravel', 'next', 'nuxt', 'express', 'deno', 'bun', 'graphql', 'prisma', 'sequelize', 'hibernate', 'jpa',
  'pandas', 'numpy', 'pytorch', 'tensorflow', 'meta', 'android', 'swift', 'gradle', 'maven', 'npm', 'webpack', 'babel',
];
const VERB = ['get', 'set', 'fetch', 'load', 'save', 'update', 'delete', 'create', 'remove', 'render', 'handle', 'parse', 'build', 'run', 'init', 'use', 'make', 'read', 'write', 'send', 'map', 'filter', 'format', 'validate', 'connect', 'close', 'open', 'push', 'pull', 'merge', 'sort', 'find', 'count', 'check', 'toggle', 'reset', 'bind', 'emit', 'listen', 'dispatch', 'select', 'insert', 'query', 'encode', 'decode', 'encrypt', 'hash', 'compile', 'deploy', 'cancel'];
const NOUN = ['user', 'account', 'order', 'product', 'item', 'list', 'page', 'route', 'request', 'response', 'token', 'session', 'config', 'query', 'cache', 'buffer', 'stream', 'file', 'path', 'event', 'state', 'props', 'store', 'model', 'view', 'component', 'service', 'client', 'server', 'socket', 'error', 'message', 'field', 'form', 'input', 'button', 'table', 'row', 'column', 'index', 'schema', 'record', 'entity', 'task', 'job', 'queue', 'worker', 'thread', 'process', 'module', 'package', 'library', 'function', 'method', 'class', 'object', 'array', 'string', 'number', 'promise', 'hook', 'context', 'provider', 'reducer', 'action', 'selector', 'router', 'guard', 'pipe', 'directive'];
const TYPE = ['', 'service', 'controller', 'manager', 'handler', 'component', 'model', 'view', 'store', 'context', 'provider', 'factory', 'helper', 'util', 'config', 'client', 'server', 'module', 'hook', 'reducer', 'action', 'selector', 'repository', 'adapter', 'builder', 'validator', 'mapper', 'resolver', 'middleware', 'wrapper', 'decorator'];

// ── general morphemes (Hungarian agglutination = real word forms + English) ──────
const HU_NOUN = ['ház', 'kert', 'fa', 'víz', 'tűz', 'föld', 'nap', 'hold', 'csillag', 'ég', 'tenger', 'folyó', 'hegy', 'város', 'falu', 'utca', 'út', 'kép', 'könyv', 'toll', 'asztal', 'szék', 'ajtó', 'ablak', 'fal', 'kéz', 'láb', 'fej', 'szem', 'fül', 'szív', 'ember', 'gyerek', 'barát', 'család', 'anya', 'apa', 'kutya', 'macska', 'madár', 'hal', 'virág', 'kenyér', 'tej', 'alma', 'munka', 'idő', 'év', 'hónap', 'óra', 'nyelv', 'szó', 'gondolat', 'élet', 'világ', 'ország', 'pénz', 'bolt', 'iskola', 'zene', 'autó', 'vonat', 'repülő', 'hajó', 'telefon', 'gép', 'fény', 'árnyék', 'hang', 'íz', 'illat', 'szín', 'forma', 'erő', 'idő', 'tér', 'hely', 'rész', 'egész', 'szám', 'betű', 'kérdés', 'válasz', 'történet', 'álom', 'terv', 'cél', 'ötlet', 'hiba', 'siker', 'remény', 'öröm', 'bánat', 'félelem', 'harag', 'szeretet', 'béke', 'háború', 'törvény', 'jog', 'rend', 'kormány', 'nép', 'nemzet', 'kultúra', 'művészet', 'tudomány', 'technika', 'orvos', 'tanár', 'diák', 'munkás', 'gazda', 'katona', 'király', 'asszony', 'férfi', 'fiú', 'lány', 'csapat', 'verseny', 'játék', 'labda', 'kapu', 'pálya', 'erdő', 'mező', 'rét', 'tó', 'patak', 'sziget', 'sivatag', 'felhő', 'eső', 'szél', 'vihar', 'jég', 'kő', 'homok', 'arany', 'ezüst', 'vas', 'üveg', 'papír', 'ruha', 'cipő', 'kalap', 'óra', 'kulcs', 'pénztárca', 'táska'];
const HU_SUF1 = ['', 'k', 't', 'ban', 'ben', 'ból', 'ből', 'ra', 're', 'ról', 'ről', 'nak', 'nek', 'val', 'vel', 'hoz', 'hez', 'tól', 'től', 'nál', 'nél', 'on', 'en', 'ön', 'ig', 'ért', 'ként', 'ba', 'be'];
const HU_SUF2 = ['', 'om', 'od', 'a', 'ja', 'unk', 'uk', 'aim', 'jai', 'aink', 'jaik'];
const HU_VERB = ['fut', 'megy', 'jön', 'lát', 'hall', 'mond', 'beszél', 'ír', 'olvas', 'tanul', 'dolgoz', 'játsz', 'eszik', 'iszik', 'alsz', 'él', 'hal', 'kezd', 'végez', 'csinál', 'épít', 'tör', 'nyit', 'zár', 'ad', 'vesz', 'visz', 'hoz', 'keres', 'talál', 'kér', 'kap', 'tud', 'akar', 'szeret', 'gondol', 'érez', 'néz', 'figyel', 'vár', 'siet'];
const HU_VSUF = ['', 'ok', 'sz', 'unk', 'tok', 'nak', 'tam', 'tál', 'ott', 'tunk', 'tatok', 'tak', 'ni', 'va', ' va', 'ható', 'hatok'];
const HU_ADJ = ['nagy', 'kis', 'szép', 'jó', 'rossz', 'új', 'régi', 'fiatal', 'öreg', 'gyors', 'lassú', 'erős', 'gyenge', 'magas', 'alacsony', 'hosszú', 'rövid', 'meleg', 'hideg', 'világos', 'sötét', 'tiszta', 'piszkos', 'könnyű', 'nehéz', 'egyszerű', 'bonyolult', 'okos', 'kedves', 'boldog'];
const HU_ASUF = ['', 'abb', 'ebb', 'an', 'en', 'ak', 'ek', 'ság', 'ség', 'talan', 'telen'];
const EN_WORD = ['time', 'world', 'life', 'work', 'home', 'water', 'light', 'sound', 'music', 'story', 'book', 'word', 'idea', 'mind', 'heart', 'hand', 'place', 'thing', 'people', 'family', 'friend', 'school', 'money', 'city', 'country', 'nature', 'animal', 'plant', 'food', 'health', 'science', 'history', 'art', 'game', 'sport', 'travel', 'language', 'number', 'color', 'shape', 'power', 'energy', 'system', 'process', 'design', 'value', 'force', 'space', 'field', 'level', 'group', 'point', 'line', 'order', 'change', 'growth', 'market', 'future', 'reason', 'nature'];
const EN_SUF = ['', 's', 'ed', 'ing', 'er', 'ers', 'est', 'less', 'ful', 'ness', 'like', 'able', 'ly', 'ment', 'ship', 'hood'];

const SEQ_LEN = 6;

/** LAZY generator: yields up to `target` distinct programming-style token sequences.
 *  Lazy so the caller can ingest in small chunks across idle ticks (no UI freeze). */
export function* programmingSeqs(target: number): Generator<string[]> {
  const seen = new Set<string>();
  let cur: string[] = [];
  // TECH is the INNERMOST loop so every technology (incl. python/kotlin/oracle/vite/…)
  // appears early and within the target, instead of the list tail being cut off.
  for (const v of VERB)
    for (const n of NOUN)
      for (const ty of TYPE)
        for (const t of TECH) {
          const tok = (t + v + n + ty).toLowerCase();
          if (seen.has(tok)) continue;
          seen.add(tok);
          cur.push(tok);
          if (cur.length >= SEQ_LEN) {
            yield cur;
            cur = [];
          }
          if (seen.size >= target) {
            if (cur.length) yield cur;
            return;
          }
        }
  if (cur.length) yield cur;
}

/** LAZY generator: yields up to `target` distinct general-vocabulary token sequences
 *  (ingested real list first, then HU agglutinated forms + verb/adj paradigms + EN). */
export function* generalSeqs(target: number): Generator<string[]> {
  const seen = new Set<string>();
  let cur: string[] = [];
  function* push(tok: string): Generator<string[]> {
    if (!tok || tok.length < 2 || seen.has(tok)) return;
    seen.add(tok);
    cur.push(tok);
    if (cur.length >= SEQ_LEN) {
      yield cur;
      cur = [];
    }
  }
  const groups: string[][] = [
    EXTRA_WORDS.map((w) => w.toLowerCase()),
    HU_NOUN.flatMap((n) => HU_SUF2.flatMap((s2) => HU_SUF1.map((s1) => (n + s2 + s1).toLowerCase()))),
    HU_VERB.flatMap((v) => HU_VSUF.map((s) => (v + s).toLowerCase().trim())),
    HU_ADJ.flatMap((a) => HU_ASUF.map((s) => (a + s).toLowerCase())),
    EN_WORD.flatMap((w) => EN_SUF.map((s) => (w + s).toLowerCase())),
  ];
  for (const g of groups) {
    for (const tok of g) {
      yield* push(tok);
      if (seen.size >= target) {
        if (cur.length) yield cur;
        return;
      }
    }
  }
  if (cur.length) yield cur;
}

/** Simple (blocking) seed — used by tests/small targets. The hook uses the lazy
 *  generators directly to ingest in chunks without freezing the UI. */
export function seedBulkVocab(
  learner: { ingestTokens: (t: string[], s?: string) => void },
  programming: number,
  general: number,
): void {
  for (const seq of programmingSeqs(programming)) learner.ingestTokens(seq, 'bulk:prog');
  for (const seq of generalSeqs(general)) learner.ingestTokens(seq, 'bulk:general');
}
