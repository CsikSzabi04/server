// ingest-general.mjs — OFFLINE-capable build-time ingest of GENERAL knowledge for
// the BRAIN's vocabulary (BRAIN_BUILD §3.b/§4 — the ~300k general-vocab the brain
// learns from). Owned by AI-3 (BODY / build tooling). Pulls clean plaintext from
// Wikipedia's `extracts` API (no noisy HTML) across science / history / geography /
// society / culture, in EN + HU + DE, chunks it, and writes a static seed file that
// AI-1's seed observes (→ vocab + Markov transitions + real general knowledge).
//
// Best-effort: a failed fetch is simply skipped; the build never depends on the
// network. No external npm packages (Node 18+ global fetch). Scale the vocabulary
// by adding more TOPICS and re-running.
//
// Usage:  npm run ingest:general          (or: node scripts/ingest-general.mjs --out <path>)
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SEED_VERSION = 1;

// Broad "vital article" topics — each is a real Wikipedia title (redirects followed).
const EN = [
  'Physics', 'Chemistry', 'Biology', 'Astronomy', 'Mathematics', 'Geology', 'Earth', 'Water', 'Air',
  'Energy', 'Light', 'Sound', 'Electricity', 'Magnetism', 'Atom', 'Gravity', 'Evolution', 'Cell (biology)',
  'DNA', 'Photosynthesis', 'Climate', 'Weather', 'Ocean', 'Mountain', 'Desert', 'Forest', 'Volcano',
  'Earthquake', 'Plant', 'Animal', 'Human body', 'Brain', 'Heart', 'Disease', 'Medicine', 'Food',
  'Nutrition', 'Sleep', 'History', 'Ancient Egypt', 'Ancient Rome', 'Ancient Greece', 'Middle Ages',
  'Renaissance', 'Industrial Revolution', 'World War II', 'Democracy', 'Government', 'Economics', 'Money',
  'Law', 'Philosophy', 'Logic', 'Ethics', 'Religion', 'Psychology', 'Sociology', 'Language', 'Writing',
  'Literature', 'Art', 'Music', 'Film', 'Architecture', 'Sport', 'Association football', 'Geography',
  'Continent', 'Europe', 'Asia', 'Africa', 'Country', 'City', 'Computer', 'Internet',
  'Artificial intelligence', 'Number', 'Geometry', 'Time', 'Calendar', 'Environment', 'Agriculture',
  'Transport', 'Communication', 'Science', 'Technology', 'Universe', 'Solar System', 'Star', 'Planet',
  // ── expansion: broader general coverage (more vocab, more topics the brain can discuss) ──
  'Genetics', 'Ecology', 'Bacteria', 'Virus', 'Bird', 'Fish', 'Mammal', 'Insect', 'Tree', 'Flower',
  'Immune system', 'Nervous system', 'Blood', 'Bone', 'Muscle', 'Protein', 'Vitamin', 'Force', 'Heat',
  'Temperature', 'Quantum mechanics', 'Theory of relativity', 'Molecule', 'Chemical element', 'Oxygen',
  'Carbon', 'Periodic table', 'Galaxy', 'Black hole', 'Moon', 'Sun', 'Mars', 'Jupiter', 'Algebra',
  'Calculus', 'Statistics', 'Probability', 'Prime number', 'Ancient China', 'Roman Empire',
  'French Revolution', 'Cold War', 'Civilization', 'North America', 'South America', 'Russia', 'China',
  'India', 'United States', 'Germany', 'France', 'United Kingdom', 'Japan', 'Capitalism', 'Trade',
  'Election', 'Human rights', 'War', 'Education', 'University', 'Family', 'Health', 'Vaccine', 'Painting',
  'Poetry', 'Novel', 'Theatre', 'Mythology', 'Cuisine', 'Software', 'Algorithm', 'Machine learning',
  'Robot', 'Smartphone', 'Renewable energy', 'Solar power', 'Automobile', 'Airplane', 'Train', 'Rocket',
  'Emotion', 'Memory', 'Intelligence', 'Happiness', 'Communication', 'Love', 'Cooking', 'Exercise',
];
const HU = [
  'Fizika', 'Kémia', 'Biológia', 'Csillagászat', 'Matematika', 'Föld', 'Víz', 'Energia', 'Fény',
  'Elektromosság', 'Atom', 'Evolúció', 'Sejt', 'Éghajlat', 'Időjárás', 'Óceán', 'Növény', 'Állat',
  'Emberi test', 'Agy', 'Betegség', 'Étel', 'Történelem', 'Ókori Róma', 'Demokrácia', 'Gazdaság',
  'Pénz', 'Jog', 'Filozófia', 'Vallás', 'Pszichológia', 'Nyelv', 'Irodalom', 'Művészet', 'Zene',
  'Sport', 'Labdarúgás', 'Földrajz', 'Európa', 'Magyarország', 'Számítógép', 'Internet',
  'Genetika', 'Vírus', 'Madár', 'Emlős', 'Idegrendszer', 'Vér', 'Erő', 'Molekula', 'Oxigén', 'Galaxis',
  'Hold', 'Algebra', 'Kína', 'India', 'Egyesült Államok', 'Németország', 'Franciaország', 'Japán',
  'Oroszország', 'Kapitalizmus', 'Háború', 'Oktatás', 'Szerelem', 'Szoftver', 'Robot', 'Autó',
  'Repülőgép', 'Mesterséges intelligencia', 'Emberi jogok', 'Boldogság',
];
const DE = [
  'Physik', 'Chemie', 'Biologie', 'Mathematik', 'Geschichte', 'Erde', 'Wasser', 'Energie', 'Computer',
  'Internet', 'Kunst', 'Musik', 'Sport', 'Sprache', 'Philosophie', 'Universum', 'Tier', 'Pflanze',
  'Genetik', 'Vogel', 'Säugetier', 'Baum', 'Blut', 'Kraft', 'Molekül', 'Sauerstoff', 'Galaxie', 'Mond',
  'China', 'Indien', 'Frankreich', 'Japan', 'Software', 'Roboter', 'Auto', 'Krieg', 'Liebe', 'Bildung',
];

// ── helpers ───────────────────────────────────────────────────────────────────
/** Sentence-boundary chunking (mirrors web/src/lib/files.ts chunkText). */
function chunkProse(text, size = 420, max = 6) {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const parts = clean.split(/(?<=[.!?…])\s+/);
  const chunks = [];
  let buf = '';
  for (const p of parts) {
    if (buf && (buf + ' ' + p).length > size) {
      chunks.push(buf.trim());
      buf = p;
    } else {
      buf = buf ? `${buf} ${p}` : p;
    }
    if (chunks.length >= max) break;
  }
  if (buf && chunks.length < max) chunks.push(buf.trim());
  return chunks.slice(0, max);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UA = 'AuriBrain/1.0 (https://github.com/CsikSzabi04/server) educational';

/** Clean plaintext extract from Wikipedia's API (no HTML), with retry on throttle. */
async function fetchWiki(title, lang, attempt = 0) {
  const url =
    `https://${lang}.wikipedia.org/w/api.php?format=json&action=query&prop=extracts` +
    `&explaintext=1&redirects=1&exchars=4000&titles=${encodeURIComponent(title)}`;
  try {
    const res = await fetch(url, { headers: { 'user-agent': UA }, signal: AbortSignal.timeout(12000) });
    if ((res.status === 429 || res.status >= 500) && attempt < 3) {
      await sleep(700 * (attempt + 1));
      return fetchWiki(title, lang, attempt + 1);
    }
    if (!res.ok) return '';
    const j = await res.json();
    const pages = j?.query?.pages ?? {};
    const first = Object.values(pages)[0];
    const extract = first?.extract ?? '';
    return typeof extract === 'string' ? extract.replace(/\s+/g, ' ').trim() : '';
  } catch {
    if (attempt < 2) {
      await sleep(500 * (attempt + 1));
      return fetchWiki(title, lang, attempt + 1);
    }
    return '';
  }
}

/** Bounded-concurrency map (keeps the fetch fast without hammering Wikipedia). */
async function mapLimit(items, limit, fn) {
  const out = [];
  let i = 0;
  const run = async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, run));
  return out;
}

// ── main ──────────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const outIdx = args.indexOf('--out');
  const outPath =
    outIdx >= 0 && args[outIdx + 1]
      ? resolve(process.cwd(), args[outIdx + 1])
      : resolve(HERE, '../src/brain/seed/general.ingested.ts');

  const jobs = [
    ...EN.map((title) => ({ title, lang: 'en' })),
    ...HU.map((title) => ({ title, lang: 'hu' })),
    ...DE.map((title) => ({ title, lang: 'de' })),
  ];

  const chunks = [];
  let ok = 0;
  await mapLimit(jobs, 3, async ({ title, lang }) => {
    await sleep(100 + Math.random() * 150); // gentle stagger → avoid Wikipedia throttling
    const text = await fetchWiki(title, lang);
    if (!text) return;
    ok++;
    for (const c of chunkProse(text)) chunks.push({ topic: title, text: c, source: `https://${lang}.wikipedia.org/wiki/${encodeURIComponent(title)}`, lang });
  });

  const header = `// general.ingested.ts — GENERATED by AI-3's \`npm run ingest:general\` script.
// DO NOT EDIT BY HAND. Broad general-knowledge corpus (clean Wikipedia plaintext,
// EN + HU + DE) for the BRAIN's general vocabulary. AI-1's seed observes the chunks
// (→ vocab + Markov transitions + real knowledge). Regenerate / grow:
//   npm run ingest:general        (add more TOPICS in the script and re-run)
// Runtime is offline + key-free; only THIS build script touches the network.

export const GENERAL_SEED_VERSION = ${SEED_VERSION};

export interface GeneralChunk {
  topic: string;
  text: string;
  source: string;
  lang: string;
}

export const GENERAL_CHUNKS: GeneralChunk[] = ${JSON.stringify(chunks, null, 2)};
`;

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, header, 'utf8');

  console.log(
    `[ingest:general] wrote ${chunks.length} chunks from ${ok}/${jobs.length} articles → ${outPath}`,
  );
}

main().catch((e) => {
  console.error('[ingest:general] failed:', e?.message ?? e);
  process.exit(1);
});
