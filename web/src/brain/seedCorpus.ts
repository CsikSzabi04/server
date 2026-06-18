// seedCorpus.ts — a tiny embedded corpus that "inoculates" a FRESH literal brain
// with the alphabets and a few hundred common words/sentences of Hungarian,
// English and German. After seeding, the brain already knows its letters
// (Stage 2) and has a starter vocabulary + Markov associations (Stage 3–4), so
// /brain shows a rich, REAL map from the first load — no API key, fully offline.
//
// Honest framing (BRAIN.md §19): this is statistical priming, not training a GPT.
import type { BrainLearner } from './learn';
import { PROGRAMMING_CHUNKS } from './seed/programming.gen';
import { PROGRAMMING_QA } from './seed/programmingCurated';
import { CONVO_EN, CONVO_HU, CONVO_DE, CONVO_QA } from './seed/conversation';
import { RECIPE_TEXT } from './seed/recipes';
import { KNOWLEDGE_TEXT, KNOWLEDGE_QA } from './seed/knowledge';
import { RELATIONS_EN, RELATIONS_HU, RELATIONS_QA } from './seed/relations';
// NOTE: the LARGE ingested corpora (programming.ingested ~331, general.ingested ~1122)
// are loaded with DYNAMIC import in seedIngestedCorpora() below, so they form a lazy
// chunk and stay OUT of the startup bundle (~300-400 kB lighter initial download).

/** Bump when the corpus changes so brains (re)seed/augment on next load.
 *  v6: AI-3's ingest populated programming.ingested.ts with a large website-building
 *  corpus → seedProgramming now learns from it.
 *  v7: seedProgramming now MERGES ingested + fallback chunks (max density) and 5 more
 *  build-a-website templates (blog, gallery, pricing, dashboard, todo) were added.
 *  v8: broad bilingual general-knowledge base (science, geography, life, tech…) added
 *  → talk about anything + clean-sentence answering (findKnowledge) + denser graph.
 *  v9: ~25 more knowledge topics (deeper science, history/society, arts, practical
 *  life) + accent-insensitive matching → broader, more robust clean-sentence answers.
 *  v10: +16 knowledge topics (solar system, cells/DNA, magnets, environment, deserts,
 *  forests, poles, Danube, ancient Egypt/Rome, industrial revolution, grammar, logic)
 *  + stemmed recall (inflected forms match) + M4 consolidation on load.
 *  v11: AI-3's ingested general corpus (589 Wikipedia plaintext chunks, EN/HU/DE) →
 *  real general vocabulary + knowledge.
 *  v12: +24 common-question knowledge topics (countries, world records, everyday
 *  science/tech, practical how-to) → better direct answer coverage.
 *  v13: +programming-tech knowledge (Python, Java, Kotlin, PHP, phpMyAdmin, MySQL,
 *  Oracle, SQL, Vite, Meta) + bulk programming vocabulary widened to those ecosystems
 *  and raised to 1,000,000 words.
 *  v14: programmer-oriented answering — ~24 code snippets + coding Q→A across Python,
 *  Java, Kotlin, PHP, SQL/MySQL, JS, Node (code-first answers with the official source).
 *  v15: RELATIONAL knowledge — "what goes with what" (stacks, pairings: React+Vite+Node,
 *  PHP+MySQL+PDO, Python+Django, MERN/LAMP…) wires the association graph + answers
 *  combination questions.
 *  v16: more domains taught — DevOps (Docker/Kubernetes/Git/CI-CD), mobile (Android/iOS/
 *  Flutter), AI/ML (ML/neural nets/LLM), networking (HTTP/DNS/REST), security (encryption/
 *  auth), data (JSON/regex) — answerable knowledge + relations + self-build pool. */
export const SEED_VERSION = 16;

// Alphabets (incl. Hungarian digraphs/trigraph + German umlauts/ß) so the
// character model + char-transition table fill on init.
const ALPHABETS = [
  'a á b c cs d dz dzs e é f g gy h i í j k l ly m n ny o ó ö ő p q r s sz t ty u ú ü ű v w x y z zs',
  'A Á B C CS D E É F G GY H I Í J K L M N NY O Ó Ö Ő P R S SZ T TY U Ú Ü Ű V Z ZS',
  'a b c d e f g h i j k l m n o p q r s t u v w x y z',
  'A B C D E F G H I J K L M N O P Q R S T U V W X Y Z',
  'a ä b c d e f g h i j k l m n o ö p q r s ß t u ü v w x y z',
  'A Ä B C D E F G H I J K L M N O Ö P Q R S T U Ü V W X Y Z',
  '0 1 2 3 4 5 6 7 8 9 . , ? ! : ; - ( )',
];

const HU = [
  'Szia! Hogy vagy ma? Jól vagyok, köszönöm.',
  'Engem Aurinak hívnak, egy segítőkész asszisztens vagyok.',
  'Mit szeretnél kérdezni? Szívesen segítek neked.',
  'Egy kettő három négy öt hat hét nyolc kilenc tíz.',
  'A nap kék égen ragyog, a víz hideg és tiszta.',
  'Szeretem a kávét reggel, és a teát este iszom.',
  'Hol van a könyv? A könyv az asztalon van.',
  'Miért kérdezed ezt? Mert tudni szeretném a választ.',
  'Ma jó idő van, sütött a nap egész nap.',
  'Az ember beszél, gondolkodik és tanul minden nap.',
  'A gyerek játszik a kertben, a kutya fut a réten.',
  'Kérlek segíts nekem megérteni ezt a feladatot.',
  'Igen, értem a kérdést, és mindjárt válaszolok.',
  'Nem tudom biztosan, de megpróbálom kitalálni.',
  'A ház nagy és világos, sok ablak van rajta.',
  'Szeretnék tanulni magyarul, angolul és németül is.',
  'A barátom okos, kedves és mindig segítőkész.',
  'Most dolgozom egy érdekes projekten a számítógépen.',
  'A zene szép, a könyv jó, a film izgalmas.',
  'Köszönöm szépen a segítséget, nagyon hálás vagyok.',
  'Jó reggelt, jó napot, jó estét és jó éjszakát.',
  'Hány óra van most? Három óra van délután.',
  'Az idő gyorsan telik, ha valami jót csinálunk.',
  'Auri emlékszik rád, és minden beszélgetésből tanul.',
];

const EN = [
  'Hello! How are you today? I am fine, thank you.',
  'My name is Auri, I am a helpful assistant.',
  'What would you like to ask? I am glad to help you.',
  'One two three four five six seven eight nine ten.',
  'The sun shines in the blue sky, the water is clear.',
  'I like coffee in the morning and tea in the evening.',
  'Where is the book? The book is on the table.',
  'Why do you ask this? Because I want to know the answer.',
  'The weather is nice today, the sun shone all day.',
  'People talk, think and learn something new every day.',
  'The child plays in the garden, the dog runs in the field.',
  'Please help me understand this task step by step.',
  'Yes, I understand the question and I will answer it.',
  'I am not sure, but I will try to figure it out.',
  'The house is big and bright, it has many windows.',
  'I would like to learn Hungarian, English and German.',
  'My friend is smart, kind and always helpful.',
  'I am working on an interesting project on the computer.',
  'Music is beautiful, the book is good, the film is exciting.',
  'Thank you very much for your help, I am grateful.',
  'Good morning, good afternoon, good evening and good night.',
  'What time is it now? It is three in the afternoon.',
  'Time goes fast when we do something good.',
  'Auri remembers you and learns from every conversation.',
];

const DE = [
  'Hallo! Wie geht es dir heute? Mir geht es gut, danke.',
  'Mein Name ist Auri, ich bin ein hilfreicher Assistent.',
  'Was möchtest du fragen? Ich helfe dir gerne.',
  'Eins zwei drei vier fünf sechs sieben acht neun zehn.',
  'Die Sonne scheint am blauen Himmel, das Wasser ist klar.',
  'Ich trinke morgens Kaffee und abends Tee.',
  'Wo ist das Buch? Das Buch ist auf dem Tisch.',
  'Warum fragst du das? Weil ich die Antwort wissen möchte.',
  'Das Wetter ist heute schön, die Sonne schien den ganzen Tag.',
  'Menschen sprechen, denken und lernen jeden Tag etwas Neues.',
  'Das Kind spielt im Garten, der Hund läuft auf dem Feld.',
  'Bitte hilf mir, diese Aufgabe Schritt für Schritt zu verstehen.',
  'Ja, ich verstehe die Frage und ich werde sie beantworten.',
  'Ich bin nicht sicher, aber ich versuche es herauszufinden.',
  'Das Haus ist groß und hell, es hat viele Fenster.',
  'Ich möchte Ungarisch, Englisch und Deutsch lernen.',
  'Mein Freund ist klug, nett und immer hilfsbereit.',
  'Ich arbeite an einem interessanten Projekt am Computer.',
  'Musik ist schön, das Buch ist gut, der Film ist spannend.',
  'Vielen Dank für deine Hilfe, ich bin sehr dankbar.',
  'Guten Morgen, guten Tag, guten Abend und gute Nacht.',
  'Wie spät ist es jetzt? Es ist drei Uhr nachmittags.',
  'Die Zeit vergeht schnell, wenn wir etwas Gutes tun.',
  'Auri erinnert sich an dich und lernt aus jedem Gespräch.',
];

// English Q→A pairs (the "Answering" region): simple question→answer mappings so
// the brain learns how a question maps to a reply (Stage 5). Original lines only.
const EN_QA: [string, string][] = [
  ['what is your name', 'My name is Auri.'],
  ['who are you', 'I am Auri, a local assistant in your browser.'],
  ['how are you', 'I am fine, thank you for asking.'],
  ['what can you do', 'I can remember, learn and help you answer questions.'],
  ['where do you run', 'I run locally, on your own device.'],
  ['do you need an api key', 'No, the base brain works offline without any key.'],
  ['what is two plus two', 'Two plus two is four.'],
  ['say hello', 'Hello! How can I help you today?'],
  ['thank you', 'You are welcome.'],
  ['what language do you speak', 'I speak English, and also Hungarian and German.'],
];

/**
 * Seed a FRESH brain with the INNATE base layer: the alphabet (Letters), an
 * English-first starter vocabulary + sentences (Language), simple Q→A mappings
 * (Answering), plus extra Hungarian/German coverage. Only seeds an EMPTY brain —
 * it never overwrites a brain that has already learned from real conversations.
 */
export function seedBaseBrain(learner: BrainLearner): boolean {
  if (learner.vocabSize > 0) return false;
  applyBaseSeed(learner);
  return true;
}

/**
 * Apply the FULL base corpus to the learner. Purely ADDITIVE (observe/observeTurn
 * only increment counts and add words/links — nothing is removed), so it is safe to
 * call on an already-learned brain to AUGMENT it with new knowledge on a seed-version
 * bump. seedBaseBrain() guards this for fresh brains; the hook calls it directly to
 * augment existing ones.
 */
export function applyBaseSeed(learner: BrainLearner): void {
  for (const a of ALPHABETS) learner.observe(a, 'seed:alphabet');
  // English-first language + answering
  for (const s of EN) learner.observe(s, 'seed:en');
  for (const [q, a] of EN_QA) learner.observeTurn(q, a, 'seed:en');
  for (const s of HU) learner.observe(s, 'seed:hu');
  for (const s of DE) learner.observe(s, 'seed:de');
  // essential everyday human conversation (EN/HU/DE) + common Q→A
  for (const s of CONVO_EN) learner.observe(s, 'seed:convo:en');
  for (const s of CONVO_HU) learner.observe(s, 'seed:convo:hu');
  for (const s of CONVO_DE) learner.observe(s, 'seed:convo:de');
  for (const [q, a] of CONVO_QA) learner.observeTurn(q, a, 'seed:convo');
  // broad general knowledge (talk about anything) — EN + HU sentences + Q→A
  for (const s of KNOWLEDGE_TEXT) learner.observe(s, 'seed:knowledge');
  for (const [q, a] of KNOWLEDGE_QA) learner.observeTurn(q, a, 'seed:knowledge');
  // RELATIONAL knowledge ("what goes with what"): multi-term sentences that wire the
  // association graph between related concepts + answer combination questions.
  for (const s of RELATIONS_EN) learner.observe(s, 'seed:relations:en');
  for (const s of RELATIONS_HU) learner.observe(s, 'seed:relations:hu');
  for (const [q, a] of RELATIONS_QA) learner.observeTurn(q, a, 'seed:relations');
  // AI-3's ingested general corpus (real Wikipedia plaintext, EN/HU/DE) → real general vocab
  // programming skill region + how-to-build-a-website knowledge (curated, in-bundle).
  // The LARGE ingested corpora load lazily via seedIngestedCorpora() (see below).
  for (const t of RECIPE_TEXT) learner.observe(t, 'seed:prog:recipe');
  seedProgramming(learner);
}

/**
 * Programming skill region: the curated, IN-BUNDLE concept chunks + Q→A (the offline
 * fallback). The large ingested programming corpus is added by seedIngestedCorpora().
 */
export function seedProgramming(learner: BrainLearner): void {
  for (const c of PROGRAMMING_CHUNKS) learner.observe(c.text, `seed:prog:${c.tech}`);
  for (const qa of PROGRAMMING_QA) learner.observeTurn(qa.q, qa.a, `seed:prog:${qa.tech}`);
}

/**
 * Load and seed the LARGE ingested corpora with DYNAMIC import, so this heavy text
 * (programming.ingested ~331 + general.ingested ~1122 chunks) is a lazy chunk and
 * stays OUT of the startup bundle. Called from the async hydration AFTER first paint.
 * Additive; run only when the base seed/augment ran (same seed-version gate).
 */
export async function seedIngestedCorpora(learner: BrainLearner): Promise<void> {
  try {
    const [prog, gen] = await Promise.all([
      import('./seed/programming.ingested'),
      import('./seed/general.ingested'),
    ]);
    for (const c of prog.PROGRAMMING_CHUNKS) learner.observe(c.text, `seed:prog:${c.tech}`);
    for (const c of gen.GENERAL_CHUNKS) learner.observe(c.text, `seed:general:${c.lang ?? 'xx'}`);
  } catch {
    /* corpus chunk failed to load → the curated in-bundle seed still works */
  }
}

/** Back-compat alias. */
export const seedBrain = seedBaseBrain;
