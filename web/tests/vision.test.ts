// Images in chat (vision): the proxy accepts only small, well-formed image data URLs on
// user turns — anything else is rejected before it can reach a provider.
// Run from web/:   npx --yes tsx --test tests/vision.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateMessages, MAX_IMAGES } from '../api/_guard';

const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

test('a user turn with images passes and keeps them', () => {
  const r = validateMessages([
    { role: 'system', content: 'sys' },
    { role: 'user', content: 'look', images: [PNG] },
  ]);
  assert.equal(r.ok, true);
  if (r.ok) {
    assert.deepEqual(r.messages[1].images, [PNG]);
    assert.equal('images' in r.messages[0], false);
  }
});

test('only real image data URLs, only on user turns, only a few', () => {
  const bad = [
    [{ role: 'user', content: 'x', images: ['https://evil.example/x.png'] }], // remote URL
    [{ role: 'user', content: 'x', images: ['data:image/svg+xml;base64,PHN2Zz4='] }], // svg (scriptable)
    [{ role: 'user', content: 'x', images: ['data:text/html;base64,PGgxPg=='] }],
    [{ role: 'user', content: 'x', images: [`${PNG}"><script>`] }],
    [{ role: 'assistant', content: 'x', images: [PNG] }], // only user turns
    [{ role: 'user', content: 'x', images: PNG }], // not an array
    [{ role: 'user', content: 'x', images: Array(MAX_IMAGES + 1).fill(PNG) }], // too many
    [{ role: 'user', content: 'x', images: [`data:image/png;base64,${'A'.repeat(1_600_000)}`] }], // too big
  ];
  for (const msgs of bad) assert.equal(validateMessages(msgs).ok, false, JSON.stringify(msgs).slice(0, 80));
});

test('text-only requests are unchanged', () => {
  const r = validateMessages([{ role: 'user', content: 'hi' }]);
  assert.deepEqual(r, { ok: true, messages: [{ role: 'user', content: 'hi' }] });
});
