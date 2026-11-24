// codeRunner.ts — turns a Code Project into ONE self-contained HTML document, which the
// sandboxed preview frame (public/code-frame.html) renders at /code/<slug>.
//
// How a project runs in the browser, with no dev server and no network for React:
//   • index.html is the entry (synthesized for React projects that lack one);
//   • every JS/JSX/TS/TSX module is transpiled by sucrase (JSX → react/jsx-runtime,
//     TypeScript types stripped) and its imports are rewritten to "@proj/<path>" keys;
//   • an <script type="importmap"> maps those keys to data: URLs (one per module), so
//     relative imports, CSS imports (→ injected <style>), JSON and SVG imports all work;
//   • React 18 + ReactDOM are inlined from node_modules (UMD) and exposed as ES modules
//     through tiny shims ("react", "react-dom/client", "react/jsx-runtime" …);
//   • any OTHER npm package is loaded from the esm.sh CDN at the version in package.json;
//   • an error overlay shows runtime/compile errors inside the page and reports them up.
// SECURITY: the result only ever runs in an iframe sandboxed WITHOUT allow-same-origin
// (opaque origin) — the generated code can't reach Auri's storage, cookies or session.
import { transform } from 'sucrase';
import * as ReactNS from 'react';
import * as ReactDOMNS from 'react-dom';
import { webEntry, type CodeProject } from './codeProjects';

/** React 18 UMD builds (react + react-dom), inlined into pages that import React.
 *  Passed in by the run page (Vite `?raw` imports) so this module stays node-testable. */
export interface ReactRuntime {
  react: string;
  reactDom: string;
}

export type RunBuild =
  | { kind: 'web'; html: string; errors: string[] }
  | { kind: 'notweb'; hint: string };

const MODULE_RE = /\.(m?jsx?|tsx?)$/i;
const RESOLVE_EXTS = ['.jsx', '.js', '.tsx', '.ts', '.mjs', '.json', '.css'];

/** Resolve "a/b/../c" against a base dir; null if it escapes the project root. */
function joinPath(baseDir: string, rel: string): string | null {
  const out: string[] = [];
  for (const seg of `${baseDir}/${rel}`.split('/')) {
    if (!seg || seg === '.') continue;
    if (seg === '..') {
      if (!out.length) return null;
      out.pop();
    } else out.push(seg);
  }
  return out.join('/');
}

const dirOf = (p: string): string => (p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : '');
const isLocal = (url: string): boolean => !/^([a-z][a-z0-9+.-]*:|\/\/|#)/i.test(url.trim());
const dataJs = (code: string): string => `data:text/javascript;charset=utf-8,${encodeURIComponent(code)}`;
const escapeScript = (code: string): string => code.replace(/<\/(script)/gi, '<\\/$1');
const escapeStyle = (css: string): string => css.replace(/<\/(style)/gi, '<\\/$1');
const attr = (attrs: string, name: string): string | null =>
  attrs.match(new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i'))?.slice(2).find((x) => x !== undefined) ??
  null;
const throwModule = (msg: string): string => `throw new Error(${JSON.stringify(msg)});`;

/** ES-module shims over the UMD globals, generated from the real export lists. */
function reactShims(): Record<string, string> {
  const ident = (k: string) => k !== 'default' && /^[A-Za-z_$][\w$]*$/.test(k);
  const named = (g: string, keys: string[]) => keys.filter(ident).map((k) => `export const ${k} = ${g}.${k};`).join('\n');
  const jsxRuntime = `const R = window.React;
export const Fragment = R.Fragment;
function make(type, config, key, isStatic) {
  const props = {};
  let children;
  for (const k in config) { if (k === 'children') children = config[k]; else props[k] = config[k]; }
  if (key !== undefined) props.key = key;
  if (children === undefined) return R.createElement(type, props);
  return isStatic && Array.isArray(children) ? R.createElement(type, props, ...children) : R.createElement(type, props, children);
}
export function jsx(t, c, k) { return make(t, c, k, false); }
export function jsxs(t, c, k) { return make(t, c, k, true); }
export function jsxDEV(t, c, k, s) { return make(t, c, k, s); }`;
  return {
    react: `const R = window.React;\nexport default R;\n${named('R', Object.keys(ReactNS))}`,
    'react-dom': `const D = window.ReactDOM;\nexport default D;\n${named('D', Object.keys(ReactDOMNS))}`,
    'react-dom/client': `const D = window.ReactDOM;
export const createRoot = D.createRoot;
export const hydrateRoot = D.hydrateRoot;
export default { createRoot, hydrateRoot };`,
    'react/jsx-runtime': jsxRuntime,
    'react/jsx-dev-runtime': jsxRuntime,
  };
}

/** esm.sh URL for a bare import, at the version range from package.json. */
function cdnUrl(spec: string, deps: Record<string, string>): string {
  const m = spec.match(/^(@[^/]+\/[^/]+|[^/]+)(\/.*)?$/);
  const name = m?.[1] ?? spec;
  const sub = m?.[2] ?? '';
  const range = deps[name];
  const ver = range && /^[\w.^~<>=| -]+$/.test(range) && range !== 'latest' ? `@${encodeURIComponent(range)}` : '';
  return `https://esm.sh/${name}${ver}${sub}?external=react,react-dom`;
}

// Runs first in the page: shows errors in an overlay and reports them to the host bar.
const OVERLAY = `(function(){
  function show(msg){
    msg = String(msg || 'Unknown error');
    try { parent.postMessage({ type: 'auri-run-error', message: msg.slice(0, 2000) }, '*'); } catch (_) {}
    var box = document.getElementById('__auri_err');
    if (!box) {
      box = document.createElement('pre');
      box.id = '__auri_err';
      box.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;max-height:45vh;overflow:auto;margin:0;padding:12px 14px;background:#1a0b10;color:#ffb3c1;border:1px solid #ff4d6d;border-radius:8px;font:12px/1.5 ui-monospace,Consolas,monospace;z-index:2147483647;white-space:pre-wrap';
      box.title = 'click to hide';
      box.onclick = function(){ box.remove(); };
      (document.body || document.documentElement).appendChild(box);
    }
    box.textContent = (box.textContent ? box.textContent + '\\n\\n' : '') + '\\u26a0 ' + msg;
  }
  window.addEventListener('error', function(e){ show((e.error && e.error.stack) || e.message); });
  window.addEventListener('unhandledrejection', function(e){ var r = e.reason; show((r && r.stack) || r); });
})();`;

/** Build the runnable document for a project. Pure (no DOM, no network). */
export function buildRunDocument(project: CodeProject, runtime: ReactRuntime): RunBuild {
  const files = new Map(project.files.map((f) => [f.path.replace(/^\.?\//, ''), f]));
  const entry = webEntry(project.files);
  if (!entry) {
    const hint =
      project.kind === 'python'
        ? 'python main.py'
        : project.kind === 'java'
          ? 'javac Main.java && java Main'
          : project.kind === 'node'
            ? 'npm install && npm start'
            : 'add an index.html to run it here';
    return { kind: 'notweb', hint };
  }

  let deps: Record<string, string> = {};
  try {
    const pkg = JSON.parse(files.get('package.json')?.content ?? '{}') as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    deps = { ...(pkg.devDependencies ?? {}), ...(pkg.dependencies ?? {}) };
  } catch {
    /* invalid package.json → CDN imports without versions */
  }

  const errors: string[] = [];
  const importMap: Record<string, string> = {};
  const bare = new Set<string>();
  const compiled = new Set<string>();

  const compileFile = (path: string, raw: boolean): string => {
    const key = `${raw ? '@proj-raw' : '@proj'}/${path}`;
    if (compiled.has(key)) return key;
    compiled.add(key);
    const content = files.get(path)?.content ?? '';
    let code: string;
    if (raw) code = `export default ${JSON.stringify(content)};`;
    else if (/\.css$/i.test(path))
      code = `const css = ${JSON.stringify(content)};
const s = document.createElement('style');
s.setAttribute('data-file', ${JSON.stringify(path)});
s.textContent = css;
document.head.appendChild(s);
export default css;`;
    else if (/\.json$/i.test(path)) {
      try {
        code = `export default ${JSON.stringify(JSON.parse(content))};`;
      } catch (e) {
        code = throwModule(`Invalid JSON in ${path}: ${(e as Error).message}`);
        errors.push(`${path}: invalid JSON`);
      }
    } else if (/\.svg$/i.test(path)) code = `export default ${JSON.stringify(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(content)}`)};`;
    else if (MODULE_RE.test(path)) code = compileModule(path, content);
    else code = `export default ${JSON.stringify(content)};`;
    importMap[key] = dataJs(code);
    return key;
  };

  const mapSpecifier = (spec: string, from: string): string => {
    if (/^(https?:|data:|blob:)/i.test(spec)) return spec;
    if (spec.startsWith('.') || spec.startsWith('/')) {
      const [clean, query = ''] = spec.split('?');
      const joined = joinPath(clean.startsWith('/') ? '' : dirOf(from), clean);
      const found =
        joined === null
          ? null
          : [joined, ...RESOLVE_EXTS.map((e) => joined + e), ...RESOLVE_EXTS.map((e) => `${joined}/index${e}`)].find((c) =>
              files.has(c),
            ) ?? null;
      if (found) return compileFile(found, /(^|&)raw\b/.test(query));
      const key = `@missing/${from}:${spec}`;
      importMap[key] = dataJs(throwModule(`Cannot find "${spec}" (imported from ${from})`));
      errors.push(`${from}: cannot find "${spec}"`);
      return key;
    }
    bare.add(spec);
    return spec;
  };

  const rewriteImports = (code: string, from: string): string =>
    code.replace(/(\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)(['"])([^'"\n]+)\2/g, (_m, pre: string, q: string, spec: string) =>
      `${pre}${q}${mapSpecifier(spec, from)}${q}`,
    );

  function compileModule(path: string, content: string): string {
    try {
      const ts = /\.tsx?$/i.test(path);
      const out = transform(content, {
        transforms: ts ? ['typescript', 'jsx'] : ['jsx'],
        jsxRuntime: 'automatic',
        production: true,
        disableESTransforms: true,
        filePath: path,
      }).code;
      return rewriteImports(out, path);
    } catch (e) {
      errors.push(`${path}: ${(e as Error).message}`);
      return throwModule(`Syntax error in ${path}: ${(e as Error).message}`);
    }
  }

  // ── the HTML entry ───────────────────────────────────────────────────────────
  const htmlPath = [...files.keys()].find((p) => p === 'index.html') ?? [...files.keys()].find((p) => /(^|\/)index\.html?$/i.test(p));
  let html: string;
  if (entry === 'html' && htmlPath) html = files.get(htmlPath)?.content ?? '';
  else {
    const main = ['src/main.jsx', 'src/main.tsx', 'src/index.jsx', 'src/index.tsx', 'main.jsx', 'index.jsx'].find((p) => files.has(p));
    html = `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8" />\n<meta name="viewport" content="width=device-width, initial-scale=1" />\n<title>${project.name.replace(/[&<>]/g, (c) => `&#${c.charCodeAt(0)};`)}</title>\n</head>\n<body>\n<div id="root"></div>\n<script type="module" src="/${main}"></script>\n</body>\n</html>`;
  }
  const htmlFrom = htmlPath ?? 'index.html';
  const htmlDir = dirOf(htmlFrom);
  const localFile = (url: string): string | null => {
    const clean = url.split(/[?#]/)[0];
    const p = joinPath(clean.startsWith('/') ? '' : htmlDir, clean);
    return p !== null && files.has(p) ? p : null;
  };

  // <script> tags: local module → import-map key; local classic → inlined; inline module → transpiled
  html = html.replace(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi, (whole, attrs: string, body: string) => {
    const src = attr(attrs, 'src');
    const type = (attr(attrs, 'type') ?? '').toLowerCase();
    const isModule = type === 'module';
    if (src && isLocal(src)) {
      const p = localFile(src);
      if (!p) {
        errors.push(`${htmlFrom}: cannot find "${src}"`);
        return `<script>throw new Error(${JSON.stringify(`Cannot find "${src}" (from ${htmlFrom})`)})</script>`;
      }
      if (isModule || /\.(jsx|tsx?)$/i.test(p)) return `<script type="module">import ${JSON.stringify(compileFile(p, false))};</script>`;
      return `<script>${escapeScript(files.get(p)?.content ?? '')}</script>`;
    }
    if (!src && isModule) return `<script type="module">${escapeScript(compileModule(htmlFrom, body))}</script>`;
    return whole;
  });

  // <link rel="stylesheet" href="local.css"> → inline <style>
  html = html.replace(/<link\b([^>]*?)\/?>/gi, (whole, attrs: string) => {
    const href = attr(attrs, 'href');
    if (!href || !isLocal(href) || !/stylesheet/i.test(attr(attrs, 'rel') ?? '')) return whole;
    const p = localFile(href);
    if (!p) {
      errors.push(`${htmlFrom}: cannot find "${href}"`);
      return whole;
    }
    return `<style data-file="${p}">${escapeStyle(files.get(p)?.content ?? '')}</style>`;
  });

  // local <img src="x.svg"> → inline data URL
  html = html.replace(/(<img\b[^>]*?\bsrc\s*=\s*)(["'])([^"']+)\2/gi, (whole, pre: string, q: string, src: string) => {
    const p = isLocal(src) ? localFile(src) : null;
    if (!p || !/\.svg$/i.test(p)) return whole;
    return `${pre}${q}data:image/svg+xml;charset=utf-8,${encodeURIComponent(files.get(p)?.content ?? '')}${q}`;
  });

  // ── prelude: overlay + React (if used) + import map ─────────────────────────
  const usesReact = [...bare].some((s) => s === 'react' || s.startsWith('react/') || s === 'react-dom' || s.startsWith('react-dom/'));
  const shims = usesReact ? reactShims() : {};
  for (const [k, v] of Object.entries(shims)) importMap[k] = dataJs(v);
  for (const spec of bare) if (!importMap[spec]) importMap[spec] = cdnUrl(spec, deps);

  const prelude = [
    `<script>${OVERLAY}</script>`,
    usesReact ? `<script>${escapeScript(runtime.react)}</script>\n<script>${escapeScript(runtime.reactDom)}</script>` : '',
    `<script type="importmap">${JSON.stringify({ imports: importMap })}</script>`,
  ]
    .filter(Boolean)
    .join('\n');

  if (/<head\b[^>]*>/i.test(html)) html = html.replace(/<head\b[^>]*>/i, (h) => `${h}\n${prelude}\n`);
  else if (/<html\b[^>]*>/i.test(html)) html = html.replace(/<html\b[^>]*>/i, (h) => `${h}\n<head>\n${prelude}\n</head>\n`);
  else html = `<!doctype html>\n<html>\n<head>\n<meta charset="utf-8" />\n${prelude}\n</head>\n<body>\n${html}\n</body>\n</html>`;

  return { kind: 'web', html, errors };
}
