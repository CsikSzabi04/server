// relevance.ts — the ONE relevance gate every offline BRAIN answer must pass.
//
// Why: each finder (knowledge, snippet, recall, docs link, web doc, personal fact) picks
// its best entry from as little as ONE shared word, so "who is the president of france"
// got the France definition, "what is a closure in rust" the Rust intro and
// "mi az a fork()" the forest answer — and a local answer also BLOCKS the model.
// A canned answer is only right when it is about EVERYTHING the question asks, so every
// TOPIC word of the query must be covered by the entry's own text (its keywords, title,
// question or the answer itself). Otherwise the brain stays quiet and the model / web /
// an honest "I don't know" answers instead.
import { foldWord, stemKey } from './seed/stem';
import { expandTechAliases } from './seed/techAlias';

// Words that say HOW something is asked, not WHAT it is about: question frames, function
// words, request verbs, politeness, and Hungarian suffixes left alone by a hyphen
// ("js-ben", "2022-es", "C#-ban"). Accent-free, since everything is folded first.
const FRAME = new Set(
  (
    // HU — function / question words
    'a az egy es meg is de hogy nem mi mit mik mire mivel ki kik kit ez ezt ezek azt azok ' +
    'en te o ti ok engem teged nekem neked nekunk van vannak volt lesz lehet kell ' +
    'vagy vagyok vagyunk vagytok mar csak jo jol ilyen olyan valami valamit dolog dolgot ' +
    'miert hogyan mikor hol honnan hova milyen melyik mennyi hany kozott ' +
    // HU — request verbs / politeness / framing
    'kerlek legyszi szia hello helo koszi koszonom jelent jelenti jelentese mukodik mukodnek valo ' +
    'meselj magyarazd magyarazza ismertesd mondd mondj mutasd mutass adj irj irjal ird ' +
    'keszits keszitsd csinalj csinald rola errol arrol roviden reszletesen pelda peldat peldaval ' +
    'tudsz tudod tudnal tudna szeretnem szeretnek akarom hasznal hasznalni hasznaljam hasznalata ' +
    // HU — detached suffixes
    'ban ben ba be bol rol tol nak nek val vel hoz hez ra re on et at ot ul ig nal nel ert ek ok ak ' +
    // EN
    'the an and or but not of to in on at by for from with about into as is are was were be ' +
    'been am do does did can could would should will may might must it its this that these ' +
    'those there here me my you your we our they them he she his her what who whom whose ' +
    'where which when why how please thanks thank hi hey hello tell explain describe define ' +
    'show give write create make build mean means work works use used using example some ' +
    'thing something kind way ' +
    // DE
    'der die das den dem und ist sind ein eine einen was wie warum wer wo ich du nicht mit ' +
    'von zu fur bitte erklare'
  ).split(/\s+/),
);

const normalize = (text: string): string => foldWord(expandTechAliases(text));

/** The words a question is ABOUT (folded, ≥ 2 chars, no question/function words). */
export function topicWords(text: string): string[] {
  const words = normalize(text).match(/[a-z0-9]+/g) ?? [];
  return [...new Set(words.filter((w) => w.length >= 2 && !FRAME.has(w)))];
}

// Inflections (folded) that may follow a word and still name the same thing.
// SHORT_BASE: safe even after a 3–4-letter word — "víz"→"vízben", "tömb"→"tömböt",
// "fájl"→"fájlt". Deliberately NOT "at/et/en/on/er" there: "form"→"format",
// "plan"→"planet", "list"→"listen", "sock"→"socket" are different words.
const SHORT_BASE = new Set(
  ('ban ben ba be bol rol tol nak nek val vel kal kel hoz hez ra re nal nel ert ig ul ' +
    'ot ok ek ak ja je juk unk tok tek ing ed es s').split(' '),
);
// After a longer (≥ 5-letter) word anything from the inflection list may follow, once
// or chained twice: "javascript"→"javascriptben", "kvantumszámítógép"→"…gépekről".
const LONG_BASE = new Set([
  ...SHORT_BASE,
  ...('at et ot on en ai ei a e i k t m d n er ers ly ies ment kent as es os okat eket akat'.split(' ')),
]);

/** Is `l` = `s` + an inflection? (single-letter t/k/m/d need a 4+ letter base: fájl→fájlt, but never for→fork) */
function inflectionOf(s: string, l: string): boolean {
  if (s.length < 3 || !l.startsWith(s)) return false;
  const suf = l.slice(s.length);
  if (s.length < 5) return SHORT_BASE.has(suf) || (s.length === 4 && /^[tkmd]$/.test(suf));
  if (LONG_BASE.has(suf)) return true;
  for (let i = 1; i < suf.length; i++) if (LONG_BASE.has(suf.slice(0, i)) && LONG_BASE.has(suf.slice(i))) return true;
  return false;
}

/** Do two folded words name the same thing? (inflection-tolerant, but never "fork"≈"forest") */
function sameWord(a: string, b: string): boolean {
  if (a === b) return true;
  const [s, l] = a.length <= b.length ? [a, b] : [b, a];
  // the same SPECIFIC stem: "működik" ~ "működés" (→ "mukod"). Short stems are too
  // ambiguous across HU/EN suffixes: "fork"/"forest" → "for", "planet"/"plants" → "plan".
  const st = stemKey(s);
  if (st.length >= 5 && st === stemKey(l)) return true;
  // one word plus a real inflection: tömb ~ tömböt, python ~ pythonban, fork ~ forks
  return inflectionOf(s, l);
}

/** Folded vocabulary (word set) of an entry's texts. */
function vocabOf(texts: (string | undefined)[]): Set<string> {
  return new Set(normalize(texts.filter(Boolean).join(' ')).match(/[a-z0-9]+/g) ?? []);
}

/**
 * Is this entry (given by its texts: keywords, title, question, answer…) about EVERY
 * topic word of the query? A query with no topic words ("ki vagy?") is not contradicted.
 */
export function coversQuery(query: string, ...texts: (string | undefined)[]): boolean {
  const topics = topicWords(query);
  if (topics.length === 0) return true;
  const vocab = vocabOf(texts);
  return topics.every((w) => {
    if (vocab.has(w)) return true;
    for (const v of vocab) if (sameWord(w, v)) return true;
    return false;
  });
}
