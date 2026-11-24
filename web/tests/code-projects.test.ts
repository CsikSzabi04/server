// Code Projects: Auri writes the files itself (parseReply → applyOps), and web projects
// compile into one runnable document for /code/<slug> (buildRunDocument).
// Run from web/:   npx --yes tsx --test tests/code-projects.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyOps, parseReply, sanitizePath, undoChanges } from '../src/lib/codeEdits';
import { buildRunDocument } from '../src/lib/codeRunner';
import { projectSlug, webEntry, type CodeProject } from '../src/lib/codeProjects';

const FAKE_RUNTIME = { react: 'window.React={};', reactDom: 'window.ReactDOM={};' };
const project = (files: Record<string, string>, kind: CodeProject['kind'] = 'react'): CodeProject => ({
  id: 'p1',
  name: 'Első web',
  kind,
  files: Object.entries(files).map(([path, content]) => ({ path, content })),
  createdAt: '',
  updatedAt: '',
});
const decodeModule = (html: string, key: string): string => {
  const map = JSON.parse(html.match(/<script type="importmap">([\s\S]*?)<\/script>/)?.[1] ?? '{}').imports as Record<string, string>;
  return decodeURIComponent(map[key].replace(/^data:text\/javascript;charset=utf-8,/, ''));
};

test('a reply with several named files writes, creates and deletes them', () => {
  const reply = [
    'Elkészítettem a portfólió oldalt és a stílust.',
    '```html index.html',
    '<!doctype html><html><body><div id="root"></div></body></html>',
    '```',
    '**src/styles.css**',
    '```css',
    'body { margin: 0; }',
    '```',
    '```jsx',
    '// src/App.jsx',
    'export default function App() { return <h1>Hi</h1>; }',
    '```',
    '```bash',
    'npm install',
    '```',
    'DELETE: README.md',
  ].join('\n');
  const base = [
    { path: 'index.html', content: 'old\n' },
    { path: 'src/App.jsx', content: 'old app\n' },
    { path: 'README.md', content: '# x\n' },
  ];
  const parsed = parseReply(reply, 'src/App.jsx');
  assert.deepEqual(parsed.ops.map((o) => o.path), ['index.html', 'src/styles.css', 'src/App.jsx']);
  assert.equal(parsed.loose.length, 1); // the bash block is shown, not written
  assert.deepEqual(parsed.deletes, ['README.md']);
  assert.equal(parsed.prose, 'Elkészítettem a portfólió oldalt és a stílust.');

  const { files, changes } = applyOps(base, parsed, true);
  assert.deepEqual(files.map((f) => f.path), ['index.html', 'src/App.jsx', 'src/styles.css']);
  assert.equal(files.find((f) => f.path === 'src/App.jsx')?.content.startsWith('export default'), true); // comment line stripped
  assert.deepEqual(
    changes.map((c) => `${c.path}:${c.kind}`),
    ['index.html:updated', 'src/styles.css:created', 'src/App.jsx:updated', 'README.md:deleted'],
  );
  // undo restores the exact previous files
  assert.deepEqual(
    undoChanges(files, changes).sort((a, b) => a.path.localeCompare(b.path)),
    base.slice().sort((a, b) => a.path.localeCompare(b.path)),
  );
});

test('streaming: the file being written shows live, but a cut-off file is never saved', () => {
  const partial = 'Kész:\n```jsx src/App.jsx\nexport default function App() {\n  return <h1>Hel';
  const base = [{ path: 'src/App.jsx', content: 'GOOD\n' }];
  const live = applyOps(base, parseReply(partial), false);
  assert.equal(live.writing, 'src/App.jsx');
  assert.match(live.files[0].content, /<h1>Hel$/);
  const final = applyOps(base, parseReply(partial), true);
  assert.equal(final.files[0].content, 'GOOD\n');
  assert.equal(final.changes[0].kind, 'cut');
});

test('one unnamed block goes into the open file only if its language fits', () => {
  assert.equal(parseReply('```jsx\nexport default 1;\n```', 'src/App.jsx').ops[0]?.path, 'src/App.jsx');
  assert.equal(parseReply('```bash\nnpm i\n```', 'src/App.jsx').ops.length, 0);
  assert.equal(parseReply('```python\nprint(1)\n```', 'src/App.jsx').ops.length, 0);
});

test('a README with inner fences survives inside a 4-backtick block', () => {
  const r = parseReply('````md README.md\n# App\n```bash\nnpm run dev\n```\n````');
  assert.equal(r.ops[0].path, 'README.md');
  assert.match(r.ops[0].code, /```bash\nnpm run dev\n```/);
});

test('paths are confined to the project', () => {
  for (const bad of ['../secret.txt', '/etc/passwd', 'C:\\Windows\\x.dll', 'a/../../b.js', 'src//x.js', '<script>.js'])
    assert.equal(sanitizePath(bad), null, bad);
  assert.equal(sanitizePath('./src/App.jsx'), 'src/App.jsx');
  assert.equal(parseReply('```js ../../evil.js\nx\n```').ops.length, 0);
  assert.equal(parseReply('DELETE: ../outside.txt').deletes.length, 0);
  // never deletes the last file
  const only = [{ path: 'index.html', content: 'x' }];
  assert.equal(applyOps(only, parseReply('DELETE: index.html'), true).files.length, 1);
});

test('the run address is a clean slug', () => {
  assert.equal(projectSlug('Első web'), 'elso-web');
  assert.equal(projectSlug('  Árvíztűrő Tükörfúrógép!! '), 'arvizturo-tukorfurogep');
});

test('a React project compiles into one sandbox-ready document', () => {
  const p = project({
    'index.html': '<!doctype html><html><head><title>t</title><link rel="stylesheet" href="/src/base.css"></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>',
    'src/main.jsx': "import { createRoot } from 'react-dom/client';\nimport App from './App';\nimport './index.css';\ncreateRoot(document.getElementById('root')).render(<App />);",
    'src/App.jsx': "import { useState } from 'react';\nimport data from './data.json';\nimport confetti from 'canvas-confetti';\nexport default function App() { const [n] = useState(data.n); return <><h1>{n}</h1><p>x</p></>; }",
    'src/index.css': 'h1 { color: red; }',
    'src/base.css': 'body { margin: 0 }',
    'src/data.json': '{"n": 3}',
    'package.json': '{"dependencies":{"react":"^18.3.1","canvas-confetti":"^1.9.3"}}',
  });
  assert.equal(webEntry(p.files), 'html');
  const r = buildRunDocument(p, FAKE_RUNTIME);
  assert.equal(r.kind, 'web');
  if (r.kind !== 'web') return;
  assert.deepEqual(r.errors, []);
  const html = r.html;
  assert.match(html, /<script type="module">import "@proj\/src\/main\.jsx";<\/script>/);
  assert.match(html, /<style data-file="src\/base\.css">body \{ margin: 0 \}<\/style>/); // <link> inlined
  assert.ok(html.indexOf('window.React={}') < html.indexOf('type="importmap"')); // React before modules
  const main = decodeModule(html, '@proj/src/main.jsx');
  assert.match(main, /from "react\/jsx-runtime"|from 'react\/jsx-runtime'/); // JSX compiled
  assert.match(main, /'@proj\/src\/App\.jsx'/); // extension resolved
  assert.match(decodeModule(html, '@proj/src/index.css'), /createElement\('style'\)/);
  assert.match(decodeModule(html, '@proj/src/data.json'), /export default \{"n":3\}/);
  assert.match(decodeModule(html, 'react'), /export const useState = R\.useState;/);
  const map = JSON.parse(html.match(/<script type="importmap">([\s\S]*?)<\/script>/)?.[1] ?? '{}').imports;
  assert.equal(map['canvas-confetti'], 'https://esm.sh/canvas-confetti@%5E1.9.3?external=react,react-dom');
});

test('missing files are reported, non-web projects get a run hint', () => {
  const r = buildRunDocument(
    project({ 'index.html': '<body><script src="app.js"></script><script type="module">import "./nope.js";</script></body>' }, 'js'),
    FAKE_RUNTIME,
  );
  assert.equal(r.kind, 'web');
  if (r.kind === 'web') assert.equal(r.errors.length, 2);
  const py = buildRunDocument(project({ 'main.py': 'print(1)' }, 'python'), FAKE_RUNTIME);
  assert.deepEqual(py, { kind: 'notweb', hint: 'python main.py' });
});
