// Regression tests for the BRAIN's direct (no-model) answers — from two real
// screenshots (2026-11-20) where the BRAIN answered:
//   "ki vagy?"                                  → the human body   ("vagy" ⊃ "agy")
//   "de a brain miért nem tud jól válaszolni?"  → the weather      ("brain" ⊃ "rain")
//   "nem" / "nmem" / "mi a …?" (even LOGGED OUT) → the user's whole personal profile
// + the privacy rule that followed: personal data never goes into the brain.
//
// Lives outside src/ so it does not affect `npm run typecheck` or the Vite build.
// Run from web/:   npx --yes tsx --test tests/brain-answers.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findKnowledge, KNOWLEDGE } from '../src/brain/seed/knowledge';
import { detectLang } from '../src/brain/lang';
import { pickFacts } from '../src/brain/answer';
import { isPersonal, setOwnNames } from '../src/brain/privacy';
import type { Memory } from '../src/lib/memory';

/** The topic the BRAIN would answer with (null = it stays silent → web / model answers). */
function topicFor(query: string): string | null {
  const answer = findKnowledge(query, detectLang(query));
  if (answer === null) return null;
  return KNOWLEDGE.find((e) => e.en === answer || e.hu === answer)?.topic ?? '?';
}

test('the screenshot bugs: no more random-topic answers', () => {
  assert.equal(topicFor('de a brain miért nem tud jól válaszolni?'), null); // was: weather
  assert.equal(topicFor('hogy vagy?'), null); // was: human-body
  assert.equal(topicFor('nem'), null);
  assert.equal(topicFor('nmem'), null);
  assert.equal(topicFor('széles ez az ablak'), null); // was: weather ("szél")
});

test('"who are you" questions get Auri’s own introduction, in the right language', () => {
  assert.equal(topicFor('ki vagy?'), 'auri'); // was: human-body, in English
  assert.match(findKnowledge('ki vagy?', detectLang('ki vagy?')) ?? '', /^Auri vagyok/);
  assert.equal(topicFor('mutatkozz be'), 'auri');
  assert.equal(topicFor('who are you'), 'auri');
  assert.equal(topicFor('ki vagyok én?'), null); // "who am I" is NOT about Auri
});

test('tasks, comparisons and troubleshooting go to the model, not a canned definition', () => {
  assert.equal(topicFor('írj egy python függvényt ami rendez egy listát'), null); // was: python
  assert.equal(topicFor('miért nem működik a kódom?'), null); // was: programming
  assert.equal(topicFor('segíts megírni egy login oldalt react-ben'), null); // was: react-lib
  assert.equal(topicFor('mi a különbség a mysql és az oracle között?'), null); // was: oracle
  assert.equal(topicFor('milyen idő van ma?'), null); // real-time → web / model
});

test('genuine knowledge questions still answer from the BRAIN (no regressions)', () => {
  const keep: Record<string, string> = {
    'mi a víz?': 'water',
    'mesélj a Napról': 'sun',
    'mi az a python': 'python',
    'what is gravity': 'gravity',
    'miért kék az ég': 'sky-blue',
    'hogyan működik a docker': 'docker',
    'a Föld': 'earth',
    python: 'python',
    'mi az a json': 'json',
    'Mi Magyarország fővárosa?': 'hungary',
    'hány ember él a Földön?': 'population',
    'why does it rain': 'rain-cause',
    'what is an orm': 'orm',
    'mi az a fotoszintézis': 'photosynthesis',
    'tell me about the moon': 'moon',
    'mit tudsz a vulkánokról?': 'volcano',
    'mi az a react': 'react-lib',
    'explain dns': 'dns',
    'víz?': 'water',
    'mi a gépi tanulás': 'machine-learning',
    'mi az a kubernetes': 'kubernetes',
  };
  for (const [q, topic] of Object.entries(keep)) assert.equal(topicFor(q), topic, q);
});

test('language detection for short accent-free Hungarian', () => {
  assert.equal(detectLang('ki vagy?'), 'hu'); // was: en
  assert.equal(detectLang('a Föld'), 'hu'); // was: en
  assert.equal(detectLang('nem'), 'hu');
  assert.equal(detectLang('what is gravity'), 'en');
  assert.equal(detectLang('who are you'), 'en');
});

// Fictional person — NEVER put real personal data into tests or seeds.
const FAKE_PROFILE =
  'Teszt Elek (Elek), született 2001. március 5., Szeged. Programtervező informatikus hallgató, a PéldaSoft fő fejlesztője.';

test('a pinned profile fact is only used when the message is actually about it', () => {
  const profile = { kind: 'fact', content: FAKE_PROFILE, weight: 1, pinned: true } as unknown as Memory;
  const coffee = { kind: 'fact', content: 'A kávét cukor nélkül szereti.', weight: 1 } as unknown as Memory;

  assert.deepEqual(pickFacts([profile, coffee], 'nem'), []); // was: [profile]
  assert.deepEqual(pickFacts([profile, coffee], 'nmem'), []); // was: [profile]
  assert.deepEqual(pickFacts([profile, coffee], 'mi a példasoft?'), [profile.content]);
  assert.deepEqual(pickFacts([profile, coffee], 'hogyan szeretem a kávét?'), [coffee.content]);
});

test('PRIVACY: personal data is recognised, so the brain never learns or recalls it', () => {
  // must be blocked from the brain
  for (const t of [
    FAKE_PROFILE,
    '2001. március 5-én születtem Szegeden.',
    'A nevem Teszt Elek.',
    'Eleknek hívnak.',
    'Szegeden lakom, a címem Fő utca 1.',
    'írj nekem a teszt.elek@example.com címre',
    'a telefonszámom +36 30 123 4567',
    'a jelszavam hunter2',
    'My name is Test Elek and I was born on 2001-03-05.',
    'I live in Szeged.',
    'Szegeden élek.', // found by the docs review 2026-11-21 (was not caught)
    'Budapesten élünk a családdal.',
    'hívj fel: +36 30 123 4567', // phone numbers without the word "telefonszám"
    'ez a számom: 06 30 123 4567',
    'call me at 555-123-4567',
    'a személyi igazolványom száma',
    'Teszt Elek, 2001. március 5.', // a full date (with day) still counts
    'dátum: 2001-03-05',
  ]) {
    assert.equal(isPersonal(t), true, t);
  }
  // the profile owner's own name, when known, is also blocked
  assert.equal(isPersonal('Elek ma programozott', ['Teszt Elek', 'Elek']), true);
  assert.equal(isPersonal('Az elektron negatív töltésű.', ['Teszt Elek']), false); // name inside a word

  // ordinary programming / knowledge talk must still be learnable
  for (const t of [
    'mi az a python',
    'írj egy react komponenst ami listát renderel',
    'hogyan működik a docker',
    'ki vagy?',
    'mi a neved?',
    'hogy hívnak?',
    'what is gravity',
    'A JSON egyszerű szöveges adatformátum kulcs–érték párokból.',
    'A gráf csúcsokból és élekből áll; az élek irányítottak lehetnek.', // 'élek' = edges
    'Élek és csúcsok bejárása BFS-sel.',
    'color: rgb(59 130 246 / 50%);', // CSS colours are not phone numbers (2026-11-21)
    'hsl(210 40% 98%) és rgb(0 128 255)',
    'Egy jó UI-nak személyisége van; a márka személyiségét a színek adják.', // ≠ személyi igazolvány
    'A React 19 2024. decemberben jelent meg.', // release month, no day → not a birthday
    'a 2025. novemberi kiadás újdonságai',
  ]) {
    assert.equal(isPersonal(t), false, t);
  }
});

test('PRIVACY: the signed-in profile name is blocked on EVERY path (registered once)', () => {
  // found 2026-11-21: distill() called isPersonal(query) without the profile names, so
  // "write a portfolio of me, <full name>" could be learned. Now the memory layer registers
  // the names once and every isPersonal() call checks them.
  try {
    setOwnNames(['Teszt Elek', 'Minta Máté']);
    for (const t of [
      'írj egy portfólió oldalt rólam, Teszt Elek',
      'Eleknek szól ez a levél',
      'Elekkel beszéltem a projektről',
      'Mate irta ezt a kodot', // accent-free typing
      'Mátéval programoztunk',
    ]) {
      assert.equal(isPersonal(t), true, t);
    }
    for (const t of ['Az elektron negatív töltésű.', 'mi az a python', 'írj egy react komponenst']) {
      assert.equal(isPersonal(t), false, t);
    }
  } finally {
    setOwnNames([]); // logout
  }
  assert.equal(isPersonal('Eleknek szól ez a levél'), false); // names gone after logout
});
