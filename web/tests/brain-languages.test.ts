// Tests for the BRAIN's programming-languages pack (seed v17): the new knowledge answers,
// code examples and sources are reachable — including "C#", "C++", ".NET" and "C",
// whose symbols/short names the tokenizers used to drop — WITHOUT stealing unrelated
// questions (word-start matching only, tasks still go to the model).
// Run from web/:   npx --yes tsx --test tests/brain-languages.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findKnowledge, KNOWLEDGE } from '../src/brain/seed/knowledge';
import { findSnippet, PROGRAMMING_SNIPPETS, isProgrammingQuery } from '../src/brain/seed/programmingCurated';
import { findSource, TECHS } from '../src/brain/seed/sources';
import { LANG_KNOWLEDGE, LANG_QA } from '../src/brain/seed/languages';
import { LANG_CHUNKS } from '../src/brain/seed/languages.corpus';
import { detectLang } from '../src/brain/lang';
import { isPersonal } from '../src/brain/privacy';

const topicFor = (query: string): string | null => {
  const answer = findKnowledge(query, detectLang(query));
  if (answer === null) return null;
  return KNOWLEDGE.find((e) => e.en === answer || e.hu === answer)?.topic ?? '?';
};

test('every listed language/tech has a clean knowledge answer (HU + EN)', () => {
  const expected: Record<string, string> = {
    'mi az a html': 'html',
    'mi a css?': 'css',
    'mi az a typescript': 'typescript',
    'mi az a c#?': 'csharp',
    'C#': 'csharp',
    'mi a c++': 'cpp',
    'c++': 'cpp',
    'mi a c?': 'c-lang',
    'mi a c nyelv': 'c-lang',
    'what is the c language': 'c-lang',
    'mi az a .net 10': 'dotnet',
    'what is .NET': 'dotnet',
    'mi az a wpf': 'wpf',
    'mi az a maui': 'maui',
    'mi az az mui': 'mui',
    'mi az a wps': 'wps',
    'mi az a vpn?': 'vpn',
    'mi az a linux': 'linux',
    'what is bash': 'bash',
    'mi az a powershell': 'powershell',
    'mi az a windows': 'windows',
    'mi az a wsl': 'wsl',
    'mi az a go nyelv': 'golang',
    'what is rust': 'rust',
    'mi az a változó': 'variable',
    'mi a ciklus': 'loop',
    'mi az a függvény': 'function',
    'mi a rekurzió': 'recursion',
    'mi az az algoritmus': 'algorithm',
    'mi az objektumorientált programozás': 'oop',
    'melyik programozási nyelvet tanuljam először?': 'programming-languages',
  };
  for (const [q, topic] of Object.entries(expected)) assert.equal(topicFor(q), topic, q);
});

test('the answer comes in the asker’s language', () => {
  assert.match(findKnowledge('mi az a c#?', 'hu') ?? '', /^A C# a Microsoft/);
  assert.match(findKnowledge('what is c#', 'en') ?? '', /^C# is Microsoft/);
});

test('no false hits: short names stay whole words, tasks go to the model', () => {
  assert.equal(topicFor('trust me'), null); // "trust" ⊅ rust
  assert.equal(topicFor('mi a cél?'), null); // "mi a c" must end there
  assert.equal(topicFor('mi az a csapat'), null);
  assert.equal(topicFor('írj egy c# programot ami összead két számot'), null); // task
  assert.equal(topicFor('mi a különbség a c# és a java között'), null); // comparison
  assert.notEqual(topicFor('melyik nyelven beszélsz?'), 'programming-languages');
  assert.notEqual(topicFor('nyisd ki az ablakot'), 'windows');
});

test('code examples are found for real how-to questions (EN + HU)', () => {
  const expected: Record<string, string> = {
    'hello world in c': 'Hello world in C',
    'hello world in c++': 'Hello world in C++',
    'hello world in c#': 'Hello world in C#',
    'for loop in c': 'For loop in C',
    'foreach loop in c#': 'For and foreach loop in C#',
    'how to read a file in c': 'Read a file in C',
    'for ciklus pythonban': 'Python for loop',
    'hogyan csináljak táblázatot html-ben': 'Table in HTML',
    'hogyan írjak függvényt bashben': 'Function in Bash',
    'dotnet new console': 'Create a console app with the dotnet CLI (.NET 10)',
    'how to install wsl': 'Install WSL (Linux on Windows)',
    'wireguard config': 'WireGuard VPN client config',
    'goroutine channel example in golang': 'Goroutine and channel in Go (golang)',
  };
  for (const [q, title] of Object.entries(expected)) assert.equal(findSnippet(q)?.title, title, q);
  // conceptual questions and unrelated talk fall through (→ knowledge / model)
  assert.equal(findSnippet('mi az a változó'), null);
  assert.equal(findSnippet('fish and chips in town'), null);
});

test('official sources resolve by tech, never by a word fragment', () => {
  assert.equal(findSource('c# docs')?.tech, 'csharp');
  assert.equal(findSource('.NET 10 docs')?.tech, 'dotnet');
  assert.notEqual(findSource('i trust you')?.tech, 'rust');
  assert.equal(isProgrammingQuery('c# linq'), true);
});

test('3D brain wiring: every example has a tech hub, topics are unique', () => {
  const hubs = new Set<string>(TECHS);
  for (const s of PROGRAMMING_SNIPPETS) assert.ok(hubs.has(s.tech), `no hub for ${s.tech} (${s.title})`);
  const topics = KNOWLEDGE.map((e) => e.topic);
  assert.equal(new Set(topics).size, topics.length, 'duplicate knowledge topic');
  assert.equal(KNOWLEDGE[0].topic, 'auri'); // identity entry stays first
});

test('PRIVACY: the pack contains no personal data, so nothing of it is filtered out', () => {
  const texts = [
    ...LANG_KNOWLEDGE.flatMap((e) => [e.en, e.hu]),
    ...LANG_QA.flatMap((x) => [x.q, x.a]),
    ...LANG_CHUNKS.map((c) => c.text),
  ];
  const flagged = texts.filter((t) => isPersonal(t));
  assert.deepEqual(flagged, []);
});
