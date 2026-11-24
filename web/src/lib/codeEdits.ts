// codeEdits.ts — turns an Auri reply into FILE EDITS for a Code Project, so Auri writes
// straight into the project (no "Apply" click): create, overwrite and delete files.
//
// Reply format (taught by the system prompt in CodeProjects):
//   ```jsx src/App.jsx          ← fence info = language + relative path
//   …the whole new file…
//   ```
//   DELETE: src/old.js          ← a line outside code blocks
// Also understood, because models do it anyway: `path=` / `title="…"` / `file=` in the
// info string, a path on the line right before the fence (**src/App.jsx**), or a first
// line comment naming the file (// src/App.jsx). 4+ backtick fences may contain ``` .
//
// SAFETY: paths are sanitized (relative, no "..", no drive letters, plain characters)
// and only ever address files INSIDE this project — a project is just a list of
// {path, content} entries in the user's own storage; nothing touches the disk. Delete
// only removes files that exist, and never the last one. Pure functions, no DOM.
import type { CodeFile } from './codeProjects';

export interface FileOp {
  path: string;
  lang: string;
  code: string;
  complete: boolean; // the closing fence arrived (false while streaming / when cut off)
}
export interface LooseBlock {
  lang: string;
  code: string;
  complete: boolean;
}
export interface ParsedReply {
  ops: FileOp[];
  loose: LooseBlock[]; // code blocks that are NOT files (shell commands, examples)
  deletes: string[];
  prose: string;
}
export type ChangeKind = 'created' | 'updated' | 'unchanged' | 'deleted' | 'cut' | 'writing';
export interface Change {
  path: string;
  kind: ChangeKind;
  before: string | null;
  after: string | null;
  add?: number;
  del?: number;
}

const NOT_FILE_LANGS = new Set([
  'bash', 'sh', 'shell', 'zsh', 'console', 'terminal', 'powershell', 'ps', 'ps1', 'pwsh', 'cmd', 'bat', 'batch',
  'text', 'txt', 'plaintext', 'output', 'log', 'diff', '',
]);

// Which fence languages may stand for a file with this extension (for an unnamed block).
const EXT_LANGS: Record<string, string[]> = {
  html: ['html', 'htm', 'xml'],
  htm: ['html', 'htm'],
  js: ['js', 'javascript', 'mjs', 'jsx', 'node'],
  mjs: ['js', 'javascript', 'mjs'],
  jsx: ['jsx', 'js', 'javascript', 'react'],
  ts: ['ts', 'typescript'],
  tsx: ['tsx', 'ts', 'typescript', 'react'],
  css: ['css'],
  scss: ['scss', 'css'],
  json: ['json', 'jsonc'],
  py: ['py', 'python', 'python3'],
  java: ['java'],
  md: ['md', 'markdown'],
  txt: ['txt', 'text'],
};

const PATHISH = /^(?:[\w@~+\-.]+\/)*[\w@~+\-.]*[\w@~+\-]\.[A-Za-z0-9]{1,10}$|^(?:[\w@~+\-.]+\/)*(?:Dockerfile|Makefile|Procfile|\.env[\w.]*|\.gitignore|\.npmrc|\.prettierrc|\.editorconfig)$/;

/** A safe, project-relative path — or null. */
export function sanitizePath(raw: string): string | null {
  const s = raw.trim().replace(/^['"`]|['"`]$/g, '').replace(/\\/g, '/').replace(/^(\.\/)+/, '');
  if (!s || s.length > 160 || s.startsWith('/') || /^[a-z]:/i.test(s)) return null;
  if (!/^[\w@~+\-. /]+$/.test(s)) return null;
  const segs = s.split('/');
  if (segs.some((g) => !g.trim() || g === '.' || g === '..')) return null;
  return s;
}

const extOf = (p: string): string => (p.includes('.') ? p.slice(p.lastIndexOf('.') + 1).toLowerCase() : '');

function parseInfo(info: string): { lang: string; path: string | null } {
  const kv = info.match(/\b(?:path|file|filename|title|name)\s*[=:]\s*["']?([^"'\s]+)/i);
  const tokens = info.split(/\s+/).filter(Boolean);
  if (kv) return { lang: (tokens[0] ?? '').split(/[:=]/)[0].toLowerCase(), path: kv[1] };
  if (tokens.length === 1 && /^[\w+#-]+:[^\s]+$/.test(tokens[0])) {
    const [lang, p] = tokens[0].split(/:(.+)/);
    if (PATHISH.test(p)) return { lang: lang.toLowerCase(), path: p };
  }
  const pathTok = tokens.find((t) => PATHISH.test(t.replace(/^['"`]|['"`]$/g, '')));
  const langTok = tokens.find((t) => t !== pathTok) ?? '';
  return { lang: langTok.toLowerCase(), path: pathTok ? pathTok.replace(/^['"`]|['"`]$/g, '') : null };
}

/** "**src/App.jsx**", "`index.html`:", "File: src/App.jsx", "### src/App.jsx" → the path. */
function pathFromHeading(line: string): string | null {
  const t = line.trim();
  if (!t || t.length > 90) return null;
  const m = t.match(/^(?:#{1,6}\s*)?(?:[-*]\s*)?(?:\*\*|__)?(?:(?:file|fájl|path)\s*:\s*)?[`*_]*([\w@~+\-./]+)[`*_]*\s*:?\s*(?:\*\*|__)?\s*:?$/i);
  return m && PATHISH.test(m[1]) ? m[1] : null;
}

/** A first line like `// src/App.jsx`, `<!-- index.html -->`, `# main.py`, `/* style.css *\/`. */
function pathFromFirstLine(line: string): string | null {
  const m = line.match(/^\s*(?:\/\/|#|<!--|\/\*)\s*(?:(?:file|fájl|path)\s*:\s*)?([\w@~+\-./]+)\s*(?:-->|\*\/)?\s*$/i);
  return m && PATHISH.test(m[1]) && m[1].includes('.') ? m[1] : null;
}

/** Parse a (possibly still streaming) reply into file ops, loose blocks, deletes, prose. */
export function parseReply(text: string, activePath?: string | null): ParsedReply {
  const lines = text.split('\n');
  const ops: FileOp[] = [];
  const loose: LooseBlock[] = [];
  const deletes: string[] = [];
  const prose: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const open = lines[i].match(/^\s{0,3}(`{3,}|~{3,})\s*([^`]*)$/);
    if (!open) {
      const del = lines[i].match(/^\s*(?:[-*]\s*)?(?:\*\*)?DELETE(?:\*\*)?\s*:\s*`?([^`\s]+)`?\s*$/i);
      const dp = del ? sanitizePath(del[1]) : null;
      if (dp) deletes.push(dp);
      else prose.push(lines[i]);
      i++;
      continue;
    }
    const fence = open[1];
    const closeRe = new RegExp(`^\\s{0,3}${fence[0] === '`' ? '`' : '~'}{${fence.length},}\\s*$`);
    const body: string[] = [];
    i++;
    let closed = false;
    while (i < lines.length) {
      if (closeRe.test(lines[i])) {
        closed = true;
        i++;
        break;
      }
      body.push(lines[i]);
      i++;
    }
    const info = parseInfo(open[2].trim());
    let path = info.path;
    if (!path) {
      // a heading line right before the block (blank lines between are fine)
      let k = prose.length - 1;
      while (k >= 0 && !prose[k].trim()) k--;
      const h = k >= 0 ? pathFromHeading(prose[k]) : null;
      if (h) {
        path = h;
        prose.splice(k, 1);
      }
    }
    if (!path && body.length) {
      const f = pathFromFirstLine(body[0]);
      if (f) {
        path = f;
        body.shift();
      }
    }
    const code = body.join('\n');
    const safe = path ? sanitizePath(path) : null;
    if (safe) ops.push({ path: safe, lang: info.lang || extOf(safe), code, complete: closed });
    else loose.push({ lang: info.lang, code, complete: closed });
  }

  // ONE unnamed block whose language fits the open file → it is that file (old behaviour).
  if (!ops.length && loose.length === 1 && activePath && loose[0].complete) {
    const lang = loose[0].lang;
    if (!NOT_FILE_LANGS.has(lang) && (EXT_LANGS[extOf(activePath)] ?? [extOf(activePath)]).includes(lang)) {
      ops.push({ path: activePath, lang, code: loose[0].code, complete: true });
      loose.length = 0;
    }
  }

  return {
    ops,
    loose,
    deletes,
    prose: prose
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim(),
  };
}

const withNewline = (s: string): string => (s && !s.endsWith('\n') ? `${s}\n` : s);

/** Apply parsed ops to a project's files. `final` = the reply is finished (or stopped):
 *  incomplete blocks are then NOT written (a cut-off file never overwrites a good one),
 *  and deletes are carried out. While streaming, the block being written shows live. */
export function applyOps(
  base: CodeFile[],
  parsed: ParsedReply,
  final: boolean,
): { files: CodeFile[]; changes: Change[]; writing: string | null } {
  const before = new Map(base.map((f) => [f.path, f.content]));
  const content = new Map(before);
  const order = base.map((f) => f.path);
  const byPath = new Map<string, Change>();
  let writing: string | null = null;

  for (const op of parsed.ops) {
    const prev = before.get(op.path) ?? null;
    if (!op.complete) {
      if (final) {
        if (!byPath.has(op.path)) byPath.set(op.path, { path: op.path, kind: 'cut', before: prev, after: null });
        continue;
      }
      writing = op.path;
      content.set(op.path, op.code);
      if (!order.includes(op.path)) order.push(op.path);
      byPath.set(op.path, { path: op.path, kind: 'writing', before: prev, after: op.code });
      continue;
    }
    const after = withNewline(op.code);
    content.set(op.path, after);
    if (!order.includes(op.path)) order.push(op.path);
    const kind: ChangeKind = prev === null ? 'created' : prev.trimEnd() === after.trimEnd() ? 'unchanged' : 'updated';
    byPath.set(op.path, { path: op.path, kind, before: prev, after });
  }

  if (final) {
    for (const d of parsed.deletes) {
      if (!content.has(d) || byPath.has(d) || content.size <= 1) continue;
      byPath.set(d, { path: d, kind: 'deleted', before: content.get(d) ?? null, after: null });
      content.delete(d);
    }
  }

  return {
    files: order.filter((p) => content.has(p)).map((p) => ({ path: p, content: content.get(p) ?? '' })),
    changes: [...byPath.values()],
    writing,
  };
}

/** Undo a message's changes on the CURRENT files (created → removed, updated/deleted → restored). */
export function undoChanges(current: CodeFile[], changes: Change[]): CodeFile[] {
  let files = current.slice();
  for (const c of changes) {
    if (c.kind === 'created') files = files.filter((f) => f.path !== c.path);
    else if ((c.kind === 'updated' || c.kind === 'deleted') && c.before !== null) {
      const before = c.before;
      if (files.some((f) => f.path === c.path)) files = files.map((f) => (f.path === c.path ? { ...f, content: before } : f));
      else files = [...files, { path: c.path, content: before }];
    }
  }
  return files.length ? files : current;
}

export type DiffRow = { type: 'same' | 'add' | 'del'; text: string };

/** Compact LCS line diff; null when the files are too big to diff cheaply. */
export function diffLines(a: string, b: string): DiffRow[] | null {
  const oldL = a.split('\n');
  const newL = b.split('\n');
  const n = oldL.length;
  const m = newL.length;
  if (n * m > 2_000_000) return null;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = oldL[i] === newL[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (oldL[i] === newL[j]) {
      out.push({ type: 'same', text: oldL[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ type: 'del', text: oldL[i++] });
    else out.push({ type: 'add', text: newL[j++] });
  }
  while (i < n) out.push({ type: 'del', text: oldL[i++] });
  while (j < m) out.push({ type: 'add', text: newL[j++] });
  return out;
}

/** +added / −removed line counts for a change (approximate for huge files). */
export function diffStats(before: string | null, after: string | null): { add: number; del: number } {
  const a = before ?? '';
  const b = after ?? '';
  if (!a) return { add: b ? b.trimEnd().split('\n').length : 0, del: 0 };
  if (!b) return { add: 0, del: a.trimEnd().split('\n').length };
  const rows = diffLines(a, b);
  if (!rows) {
    const d = b.split('\n').length - a.split('\n').length;
    return { add: Math.max(0, d), del: Math.max(0, -d) };
  }
  return { add: rows.filter((r) => r.type === 'add').length, del: rows.filter((r) => r.type === 'del').length };
}
