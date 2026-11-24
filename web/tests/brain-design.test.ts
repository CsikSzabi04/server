// Tests for the BRAIN's CSS + visual design pack (seed v18): design questions get clean
// answers and working recipes; tasks still go to the model; nothing steals unrelated
// questions; the pack holds no personal data and records licence + source.
// Run from web/:   npx --yes tsx --test tests/brain-design.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findKnowledge, KNOWLEDGE } from '../src/brain/seed/knowledge';
import { findSnippet, PROGRAMMING_SNIPPETS } from '../src/brain/seed/programmingCurated';
import { TECHS } from '../src/brain/seed/sources';
import { DESIGN_KNOWLEDGE, DESIGN_QA } from '../src/brain/seed/design';
import { DESIGN_SNIPPETS } from '../src/brain/seed/designSnippets';
import { DESIGN_CHUNKS } from '../src/brain/seed/design.corpus';
import { detectLang } from '../src/brain/lang';
import { isPersonal } from '../src/brain/privacy';

const topicFor = (q: string): string | null => {
  const a = findKnowledge(q, detectLang(q));
  return a === null ? null : (KNOWLEDGE.find((e) => e.en === a || e.hu === a)?.topic ?? '?');
};

test('design questions get the right clean answer (HU + EN)', () => {
  const expected: Record<string, string> = {
    'mi az a flexbox': 'flexbox',
    'what is css grid': 'css-grid',
    'flexbox vagy grid?': 'flex-or-grid',
    'mi a box model': 'box-model',
    'mi az a container query': 'container-queries', // not docker's "container"
    'mi a :has() szelektor': 'has-selector',
    'mi az a clamp()': 'clamp',
    'mi a tipográfia': 'typography',
    'mi a színelmélet': 'color-theory',
    'what is a color palette': 'color-palette',
    'mi a 60-30-10 szabály': 'color-palette',
    'mi az az oklch': 'color-formats',
    'hogyan működik a sötét mód': 'dark-mode',
    'what is light mode': 'dark-mode', // not the physics of light
    'mi a kontrasztarány': 'contrast',
    'mi a wcag': 'contrast',
    'mi az akadálymentesség': 'web-accessibility',
    'mi a vizuális hierarchia': 'visual-hierarchy',
    'mi a gestalt': 'gestalt',
    'mi az a design system': 'design-system',
    'mi az a glassmorphism': 'glassmorphism',
    'mi a neumorphism': 'neumorphism',
    'mi az a box-shadow': 'shadows',
    'mi az a bento grid': 'ui-trends',
    'mi a bem módszer': 'bem',
    'what is a hero section': 'hero-section',
    'mi az a skeleton loader': 'loading-states',
    'mi az a css reset': 'css-reset',
    'mi a sass': 'sass',
  };
  for (const [q, topic] of Object.entries(expected)) assert.equal(topicFor(q), topic, q);
});

test('tasks and unrelated questions are not answered with a design definition', () => {
  for (const q of [
    'írj egy reszponzív oldalt css grid-del',
    'segíts megírni egy flexbox navbart',
    'készíts sötét módot az oldalamra',
    'mi a különbség a flexbox és a grid között',
    'miért van árnyék?', // physics, not box-shadow
    'ki volt Bem József?', // not BEM
    'translate this sentence to english',
    'mi az a docker container', // still docker
  ]) {
    const t = topicFor(q);
    assert.ok(t === null || !DESIGN_KNOWLEDGE.some((e) => e.topic === t), `${q} → ${t}`);
  }
  assert.equal(topicFor('hogyan működik a docker'), 'docker');
});

test('how-to questions find a working recipe', () => {
  const expected: Record<string, string> = {
    'glassmorphism card css': 'Glassmorphism card (frosted glass)',
    'skeleton loading shimmer': 'Skeleton loading placeholder with shimmer',
    'toggle switch checkbox': 'Toggle switch from a checkbox',
    'dark mode css variables': 'Dark mode with CSS variables and prefers-color-scheme',
    'hogyan csináljak sötét témát css változókkal': 'Dark mode with CSS variables and prefers-color-scheme',
    'sticky footer layout': 'Sticky footer layout (footer at the bottom)',
    'container query card': 'Container query card (responsive component)',
    'gradient text': 'Gradient text',
    'modal dialog backdrop': 'Modal dialog with the dialog element and backdrop',
    'tailwind glassmorphism panel': 'Tailwind glassmorphism panel',
  };
  for (const [q, title] of Object.entries(expected)) assert.equal(findSnippet(q)?.title, title, q);
});

test('3D wiring: a UI · design hub exists and every recipe has its hub', () => {
  assert.ok((TECHS as readonly string[]).includes('design'));
  const hubs = new Set<string>(TECHS);
  for (const s of PROGRAMMING_SNIPPETS) assert.ok(hubs.has(s.tech), s.title);
  assert.ok(DESIGN_SNIPPETS.length >= 80, `only ${DESIGN_SNIPPETS.length} recipes`);
  const titles = PROGRAMMING_SNIPPETS.map((s) => s.title);
  assert.equal(new Set(titles).size, titles.length, 'duplicate snippet title');
});

test('PRIVACY + provenance: no personal data, every corpus item has licence + source', () => {
  const texts = [
    ...DESIGN_KNOWLEDGE.flatMap((e) => [e.en, e.hu]),
    ...DESIGN_QA.flatMap((x) => [x.q, x.a]),
    ...DESIGN_CHUNKS.map((c) => c.text),
  ];
  assert.deepEqual(texts.filter((t) => isPersonal(t)), []);
  for (const c of DESIGN_CHUNKS) {
    assert.equal(c.license, 'original');
    assert.match(c.source, /^https:\/\//);
  }
});
