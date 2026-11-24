// PRIVACY regression tests — SECURITY.md §4 ("one user's personal data never reaches
// anyone else"), the browser-local half: after logout, or when a different account
// signs in on the same browser, NOTHING of the previous account may be readable.
//
// Covers: the BRAIN's local mirror, web-learned docs (they carry the user's queries),
// code projects, and the one-time hand-over of pre-scoping legacy data.
// Supabase is not configured here, so brainStore runs on its local-mirror path —
// exactly the path that used to leak (one shared 'auri.brainLearn' key for everyone).
//
// Lives outside src/ (not part of typecheck / build). Run from web/:
//   npx --yes tsx --test tests/privacy-isolation.test.ts
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// ── a Map-backed localStorage (no IndexedDB in node → idb.ts falls back to it) ──
class MemStorage {
  private m = new Map<string, string>();
  get length(): number {
    return this.m.size;
  }
  key(i: number): string | null {
    return [...this.m.keys()][i] ?? null;
  }
  getItem(k: string): string | null {
    return this.m.has(k) ? (this.m.get(k) as string) : null;
  }
  setItem(k: string, v: string): void {
    this.m.set(k, String(v));
  }
  removeItem(k: string): void {
    this.m.delete(k);
  }
  clear(): void {
    this.m.clear();
  }
}
const ls = new MemStorage();
(globalThis as unknown as { localStorage: MemStorage }).localStorage = ls;

const { brainStore, forgetLocalBrain } = await import('../src/brain/brainStore');
const { loadWebDocs, addWebDoc, getWebDocs } = await import('../src/brain/webStore');
const { setStorageScope } = await import('../src/lib/storageScope');
const { createProject, listProjects } = await import('../src/lib/codeProjects');

const A = 'user-aaaa';
const B = 'user-bbbb';
const brainOf = (tag: string) => ({
  vocab: { [tag]: 3 },
  transitions: {},
  qa: [{ q: `secret question of ${tag}`, a: `secret answer of ${tag}`, keys: [tag] }],
  trainSteps: 1,
  updatedAt: new Date().toISOString(),
});
const doc = (url: string, query: string) => ({
  url,
  title: `t ${url}`,
  snippet: 's',
  query,
  weight: 3,
  fetchedAt: new Date().toISOString(),
  ttlDays: 7,
});

beforeEach(() => {
  ls.clear();
  setStorageScope(null);
});

test('BRAIN mirror: a guest never loads a signed-in user’s brain', async () => {
  await brainStore.importJSON(A, brainOf('alpha'));
  assert.equal(await brainStore.load(null), null, 'guest must not see A');
  assert.equal(await brainStore.load(B), null, 'another account must not see A');
  const back = await brainStore.load(A);
  assert.ok(back && 'alpha' in back.vocab, 'A still gets A’s own brain');
});

test('BRAIN mirror: legacy shared key goes to the first account, never to a guest', async () => {
  ls.setItem('auri.brainLearn', JSON.stringify(brainOf('legacy')));
  assert.equal(await brainStore.load(null), null, 'guest must not read the legacy shared snapshot');
  const a = await brainStore.load(A);
  assert.ok(a && 'legacy' in a.vocab, 'first account to sign in receives it');
  assert.equal(ls.getItem('auri.brainLearn'), null, 'legacy key removed after hand-over');
  assert.equal(await brainStore.load(B), null, 'a later account does not get it');
});

test('BRAIN mirror: forgetLocalBrain removes only that user’s copy', async () => {
  await brainStore.importJSON(A, brainOf('alpha'));
  await brainStore.importJSON(B, brainOf('beta'));
  await forgetLocalBrain(A);
  assert.equal(await brainStore.load(A), null);
  const b = await brainStore.load(B);
  assert.ok(b && 'beta' in b.vocab, 'B is untouched');
});

test('BRAIN mirror: a save still pending at sign-out/deletion cannot write it back', async () => {
  await brainStore.save(A, brainOf('late')); // debounced (1.5 s) — still pending
  await forgetLocalBrain(A); // sign-out / account deletion wipes the mirror
  await new Promise((r) => setTimeout(r, 1700)); // past the debounce
  assert.equal(ls.getItem(`auri.brainLearn.u.${A}`), null, 'the late save must not re-create it');
  await brainStore.importJSON(A, brainOf('again')); // still blocked until A signs in again…
  assert.equal(ls.getItem(`auri.brainLearn.u.${A}`), null);
  await brainStore.load(A); // …which re-enables saving for A
  await brainStore.importJSON(A, brainOf('again'));
  assert.ok(ls.getItem(`auri.brainLearn.u.${A}`), 'after signing in again A can save');
});

test('web-learned docs (with the user’s queries) are per identity', async () => {
  await loadWebDocs(A);
  addWebDoc(doc('https://a.example/x', 'A private query'));
  await new Promise((r) => setTimeout(r, 5)); // let the async persist land
  await loadWebDocs(null);
  assert.equal(getWebDocs().length, 0, 'guest sees none of A’s web docs');
  await loadWebDocs(B);
  assert.equal(getWebDocs().length, 0, 'B sees none of A’s web docs');
  await loadWebDocs(A);
  assert.deepEqual(
    getWebDocs().map((d) => d.query),
    ['A private query'],
    'A gets them back',
  );
});

test('code projects made while signed in are not listed after logout', () => {
  setStorageScope(A);
  createProject('A secret project', 'js');
  assert.equal(listProjects().length, 1);
  setStorageScope(null);
  assert.equal(listProjects().length, 0, 'guest sees no projects of A');
  setStorageScope(B);
  assert.equal(listProjects().length, 0, 'B sees no projects of A');
  setStorageScope(A);
  assert.equal(listProjects()[0]?.name, 'A secret project');
});

test('legacy (unscoped) projects are handed once to the first account', () => {
  ls.setItem('auri.projects', JSON.stringify([{ id: '1', name: 'old', kind: 'js', files: [], createdAt: '', updatedAt: '' }]));
  setStorageScope(null);
  assert.equal(listProjects().length, 1, 'guest-only devices keep their old projects');
  setStorageScope(A);
  assert.equal(listProjects().length, 1, 'first account receives them');
  setStorageScope(null);
  assert.equal(listProjects().length, 0, 'and they no longer show as guest');
  setStorageScope(B);
  assert.equal(listProjects().length, 0, 'a later account never receives them');
});
