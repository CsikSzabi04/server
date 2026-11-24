// Code workspace store. Local, dependency-free: projects live in localStorage,
// each project is a set of editable files scaffolded from a language template.
// Projects can be exported as a real .zip (store method, built by hand below so
// we don't have to add a zip dependency to package.json).
import { claimLegacyLocal, scopedKey, storageScope } from './storageScope';

export type ProjectKind = 'python' | 'node' | 'react' | 'js' | 'java';

export interface CodeFile {
  path: string;
  content: string;
}

export interface CodeProject {
  id: string;
  name: string;
  kind: ProjectKind;
  files: CodeFile[];
  createdAt: string;
  updatedAt: string;
}

export interface KindMeta {
  id: ProjectKind;
  label: string;
  icon: string;
}

export const KINDS: KindMeta[] = [
  { id: 'python', label: 'Python', icon: '🐍' },
  { id: 'node', label: 'Node.js', icon: '⬢' },
  { id: 'react', label: 'React', icon: '⚛' },
  { id: 'js', label: 'JavaScript', icon: '🟨' },
  { id: 'java', label: 'Java', icon: '☕' },
];

export const kindIcon = (k: ProjectKind): string => KINDS.find((x) => x.id === k)?.icon ?? '📁';

/** Safe lowercase package/folder slug from a project name ("Első web" → "elso-web").
 *  Also the project's run address: /code/<slug>. */
export function projectSlug(name: string): string {
  return slug(name);
}

function slug(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{M}/gu, '') // strip accents (combining marks)
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'project'
  );
}

/** Starter files for a new project, per language. */
export function scaffold(kind: ProjectKind, name: string): CodeFile[] {
  const id = slug(name);
  switch (kind) {
    case 'python':
      return [
        {
          path: 'main.py',
          content: `def main() -> None:\n    print("Hello from ${name}!")\n\n\nif __name__ == "__main__":\n    main()\n`,
        },
        { path: 'requirements.txt', content: '' },
        { path: 'README.md', content: `# ${name}\n\nPython project.\n\n## Run\n\n\`\`\`bash\npython main.py\n\`\`\`\n` },
      ];
    case 'node':
      return [
        { path: 'index.js', content: `console.log("Hello from ${name}!");\n` },
        {
          path: 'package.json',
          content:
            JSON.stringify(
              { name: id, version: '1.0.0', type: 'module', main: 'index.js', scripts: { start: 'node index.js' } },
              null,
              2,
            ) + '\n',
        },
        { path: 'README.md', content: `# ${name}\n\nNode.js project.\n\n## Run\n\n\`\`\`bash\nnpm start\n\`\`\`\n` },
      ];
    case 'react':
      return [
        {
          path: 'index.html',
          content: `<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="utf-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <title>${name}</title>\n  </head>\n  <body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.jsx"></script>\n  </body>\n</html>\n`,
        },
        {
          path: 'src/main.jsx',
          content: `import { createRoot } from 'react-dom/client';\nimport App from './App.jsx';\n\ncreateRoot(document.getElementById('root')).render(<App />);\n`,
        },
        {
          path: 'src/App.jsx',
          content: `export default function App() {\n  return <h1>Hello from ${name}!</h1>;\n}\n`,
        },
        {
          path: 'package.json',
          content:
            JSON.stringify(
              {
                name: id,
                version: '1.0.0',
                type: 'module',
                scripts: { dev: 'vite', build: 'vite build', preview: 'vite preview' },
                dependencies: { react: '^18.3.1', 'react-dom': '^18.3.1' },
                devDependencies: { '@vitejs/plugin-react': '^4.3.4', vite: '^5.4.11' },
              },
              null,
              2,
            ) + '\n',
        },
        { path: 'README.md', content: `# ${name}\n\nReact + Vite project.\n\n## Run\n\n\`\`\`bash\nnpm install\nnpm run dev\n\`\`\`\n` },
      ];
    case 'js':
      return [
        {
          path: 'index.html',
          content: `<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="utf-8" />\n    <title>${name}</title>\n  </head>\n  <body>\n    <h1>${name}</h1>\n    <script src="app.js"></script>\n  </body>\n</html>\n`,
        },
        { path: 'app.js', content: `console.log("Hello from ${name}!");\n` },
        { path: 'README.md', content: `# ${name}\n\nPlain JavaScript project. Open \`index.html\` in a browser.\n` },
      ];
    case 'java':
      return [
        {
          path: 'Main.java',
          content: `public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello from ${name}!");\n    }\n}\n`,
        },
        { path: 'README.md', content: `# ${name}\n\nJava project.\n\n## Run\n\n\`\`\`bash\njavac Main.java\njava Main\n\`\`\`\n` },
      ];
  }
}

// ── localStorage persistence ────────────────────────────────────────────────
// PRIVACY (SECURITY.md §4.4): projects made while signed in live under the user's own
// key, so they don't show up after logout or for another account on this browser.
const LS_KEY = 'auri.projects';

/** The current identity's key; a signed-in user first claims any legacy guest data. */
function projectsKey(): string {
  const uid = storageScope();
  if (uid) claimLegacyLocal(LS_KEY, uid);
  return scopedKey(LS_KEY, uid);
}

function read(): CodeProject[] {
  try {
    return JSON.parse(localStorage.getItem(projectsKey()) || '[]') as CodeProject[];
  } catch {
    return [];
  }
}

function write(v: CodeProject[]): void {
  try {
    localStorage.setItem(projectsKey(), JSON.stringify(v));
  } catch {
    /* storage blocked */
  }
}

export function listProjects(): CodeProject[] {
  return read().sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
}

export function createProject(name: string, kind: ProjectKind): CodeProject {
  const now = new Date().toISOString();
  const p: CodeProject = {
    id: crypto.randomUUID(),
    name: name.trim() || 'untitled',
    kind,
    files: scaffold(kind, name.trim() || 'untitled'),
    createdAt: now,
    updatedAt: now,
  };
  const all = read();
  all.unshift(p);
  write(all);
  return p;
}

/** Persist a full project (used after editing files). */
export function saveProject(project: CodeProject): void {
  const all = read();
  const i = all.findIndex((p) => p.id === project.id);
  if (i >= 0) all[i] = project;
  else all.unshift(project);
  write(all);
}

export function renameProject(id: string, name: string): void {
  const all = read();
  const p = all.find((x) => x.id === id);
  if (p) {
    p.name = name.trim() || p.name;
    p.updatedAt = new Date().toISOString();
    write(all);
  }
}

export function deleteProject(id: string): void {
  write(read().filter((p) => p.id !== id));
}

/** The project behind /code/<slug> (most recently edited one if names collide), or by id. */
export function findProjectBySlug(s: string): CodeProject | null {
  const want = s.toLowerCase();
  return listProjects().find((p) => slug(p.name) === want) ?? read().find((p) => p.id === s) ?? null;
}

/** Can the browser run this project (an HTML page or a React entry)? null = not a web project. */
export function webEntry(files: CodeFile[]): 'html' | 'react' | null {
  const paths = new Set(files.map((f) => f.path.replace(/^\.?\//, '')));
  if ([...paths].some((p) => /(^|\/)index\.html?$/i.test(p))) return 'html';
  if (['src/main.jsx', 'src/main.tsx', 'src/index.jsx', 'src/index.tsx', 'main.jsx', 'index.jsx'].some((p) => paths.has(p)))
    return 'react';
  return null;
}

// ── Code learnings: the workspace gets better with every write ───────────────
// Self-contained, localStorage-backed. We extract the libraries/imports and the
// naming style the user actually writes, per language, and feed a short summary
// back into the code-chat system prompt so each project sharpens the next.

export interface KindLearning {
  libs: Record<string, number>;
  naming: { camel: number; snake: number };
  samples: number;
  updatedAt: string;
}
export type Learnings = Partial<Record<ProjectKind, KindLearning>>;

const LEARN_KEY = 'auri.codeLearnings';

function learningsKey(): string {
  const uid = storageScope();
  if (uid) claimLegacyLocal(LEARN_KEY, uid);
  return scopedKey(LEARN_KEY, uid);
}

function readLearnings(): Learnings {
  try {
    return JSON.parse(localStorage.getItem(learningsKey()) || '{}') as Learnings;
  } catch {
    return {};
  }
}
function writeLearnings(v: Learnings): void {
  try {
    localStorage.setItem(learningsKey(), JSON.stringify(v));
  } catch {
    /* storage blocked */
  }
}

/** Pull imported module / library names out of a file, per language. */
function extractLibs(content: string, kind: ProjectKind): string[] {
  const libs = new Set<string>();
  const add = (raw?: string) => {
    if (!raw) return;
    let name = raw.trim();
    if (!name || name.startsWith('.') || name.startsWith('/')) return; // local import
    if (name.startsWith('@')) name = name.split('/').slice(0, 2).join('/'); // scoped pkg
    else name = name.split('/')[0]; // bare pkg root
    name = name.split('.')[0]; // python / java root module
    if (name) libs.add(name);
  };

  if (kind === 'python') {
    for (const m of content.matchAll(/^\s*import\s+([\w.]+)/gm)) add(m[1]);
    for (const m of content.matchAll(/^\s*from\s+([\w.]+)\s+import/gm)) add(m[1]);
  } else if (kind === 'java') {
    for (const m of content.matchAll(/^\s*import\s+([\w.]+)\s*;/gm)) add(m[1]);
  } else {
    for (const m of content.matchAll(/import\s+(?:[\w*\s{},]+\s+from\s+)?['"]([^'"]+)['"]/g)) add(m[1]);
    for (const m of content.matchAll(/require\(\s*['"]([^'"]+)['"]\s*\)/g)) add(m[1]);
  }
  return [...libs];
}

/** Rough camelCase vs snake_case tally from identifiers. */
function namingTally(content: string): { camel: number; snake: number } {
  const snake = (content.match(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g) ?? []).length;
  const camel = (content.match(/\b[a-z]+[A-Z][a-zA-Z0-9]*\b/g) ?? []).length;
  return { camel, snake };
}

/** Learn from a whole project — call after applying or saving code. */
export function learnFromProject(project: CodeProject): void {
  const all = readLearnings();
  const cur: KindLearning =
    all[project.kind] ?? { libs: {}, naming: { camel: 0, snake: 0 }, samples: 0, updatedAt: '' };
  for (const f of project.files) {
    for (const lib of extractLibs(f.content, project.kind)) cur.libs[lib] = (cur.libs[lib] ?? 0) + 1;
    const n = namingTally(f.content);
    cur.naming.camel += n.camel;
    cur.naming.snake += n.snake;
  }
  cur.samples += 1;
  cur.updatedAt = new Date().toISOString();
  // keep the libs map bounded (top 40 by count)
  cur.libs = Object.fromEntries(Object.entries(cur.libs).sort((a, b) => b[1] - a[1]).slice(0, 40));
  all[project.kind] = cur;
  writeLearnings(all);
}

/** A short, injectable hint summarising what the user usually writes for a kind. */
export function learningsPrompt(kind: ProjectKind): string | null {
  const l = readLearnings()[kind];
  if (!l || l.samples === 0) return null;
  const libs = Object.entries(l.libs)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([n]) => n);
  const naming = l.naming.snake > l.naming.camel ? 'snake_case' : 'camelCase';
  const bits = [`prefers ${naming} naming`];
  if (libs.length) bits.unshift(`commonly uses: ${libs.join(', ')}`);
  return `Learned conventions for this user's ${kind} code — ${bits.join('; ')}. Match these unless asked otherwise.`;
}

// ── .zip export (store method, no compression, no dependency) ────────────────
function crc32(bytes: Uint8Array): number {
  let crc = ~0;
  for (let i = 0; i < bytes.length; i++) {
    crc ^= bytes[i];
    for (let j = 0; j < 8; j++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (~crc >>> 0) >>> 0;
}

const u16 = (n: number) => new Uint8Array([n & 0xff, (n >>> 8) & 0xff]);
const u32 = (n: number) =>
  new Uint8Array([n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff]);

function concat(parts: Uint8Array[]): Uint8Array {
  let len = 0;
  for (const p of parts) len += p.length;
  const out = new Uint8Array(len);
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

/** Build a valid (uncompressed) .zip Blob from a list of files. */
export function zipFiles(files: CodeFile[]): Blob {
  const enc = new TextEncoder();
  const local: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;

  for (const f of files) {
    const nameBytes = enc.encode(f.path);
    const data = enc.encode(f.content);
    const crc = crc32(data);

    const header = concat([
      u32(0x04034b50), u16(20), u16(0), u16(0), u16(0), u16(0),
      u32(crc), u32(data.length), u32(data.length),
      u16(nameBytes.length), u16(0), nameBytes,
    ]);
    local.push(header, data);

    central.push(
      concat([
        u32(0x02014b50), u16(20), u16(20), u16(0), u16(0), u16(0), u16(0),
        u32(crc), u32(data.length), u32(data.length),
        u16(nameBytes.length), u16(0), u16(0), u16(0), u16(0), u32(0),
        u32(offset), nameBytes,
      ]),
    );
    offset += header.length + data.length;
  }

  const centralStart = offset;
  let centralSize = 0;
  for (const c of central) centralSize += c.length;

  const end = concat([
    u32(0x06054b50), u16(0), u16(0),
    u16(files.length), u16(files.length),
    u32(centralSize), u32(centralStart), u16(0),
  ]);

  return new Blob([...local, ...central, end] as BlobPart[], { type: 'application/zip' });
}

/** Trigger a browser download of the project as <slug>.zip. */
export function downloadZip(project: CodeProject): void {
  const blob = zipFiles(project.files);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${slug(project.name)}.zip`;
  a.click();
  URL.revokeObjectURL(url);
}
