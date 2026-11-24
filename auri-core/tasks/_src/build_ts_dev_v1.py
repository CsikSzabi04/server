"""Generator for the aurikod-hu v1 `dev` split, TypeScript part (40 tasks, L0–L1). Owner: AI-2.

Run:  .venv\\Scripts\\python.exe tasks\\_src\\build_ts_dev_v1.py
Same 40 problems as the Python dev set (build_py_dev_v1.T): the cases are reused, the prompt is
translated (Python idioms → JS ones, ValueError → RangeError, None → null), the reference is TS.
Tests: node:test + node:assert/strict, one test per case, the call with its input as the message.
"""

from __future__ import annotations

import json
import sys
import textwrap
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_py_dev_v1 import NS, ROOT, T

TOPIC = {"py.basics": "ts.basics", "py.strings": "ts.strings", "py.collections": "ts.collections", "py.errors": "ts.errors"}
PROMPT_MAP = [
    ("a `str.split()` szerinti szavakat", "a whitespace (`/\\s+/`) mentén elválasztott, nem üres szavakat"),
    ("a `str.split()` szerinti szavak", "a whitespace (`/\\s+/`) mentén elválasztott, nem üres szavak"),
    ("(`str.isupper()`)", "(`ch !== ch.toLowerCase()`)"),
    ("(`round(x, 1)`)", "(`Math.round(x * 10) / 10`)"),
    ("(`round(x, 2)`)", "(`Math.round(x * 100) / 100`)"),
    ("(`str.isalnum()`)", "(Unicode betű vagy számjegy: `/[\\p{L}\\p{N}]/u`)"),
    ("(`str.casefold()`)", "(`toLowerCase()`)"),
    ("`str.capitalize()` szerint nagy kezdőbetűs", "nagy kezdőbetűs (első karakter nagy, a többi kicsi)"),
    ("(`str.isspace()`)", "(`/\\s/`)"),
    ("betű = `str.isalpha()`, számjegy = `str.isdigit()`, szóköz = `str.isspace()`",
     "betű = `/\\p{L}/u`, számjegy = `/\\p{Nd}/u`, szóköz = `/\\s/`"),
    ("Csak a `list` típust bontsd ki (egy tuple vagy szöveg elem marad).", "Csak a tömböket bontsd ki (egy szöveg elem marad)."),
    ("`ValueError`-t", "`RangeError`-t"),
    ("`None`", "`null`"),
    ("listára", "tömbre"), ("listát", "tömböt"), ("listája", "tömbje"), ("listává", "tömbbé"), ("listában", "tömbben"),
    ("lista", "tömb"), ("Lista", "Tömb"),
]
FORBIDDEN = ("str.", "`round(", "None", "ValueError", "tuple", "list[", "dict[", "-> ")

# python name → (ts name, ts signature, ts reference body)
TS: dict[str, tuple[str, str, str]] = {
    "paros_szamok": ("parosSzamok", "xs: number[]): number[]", "return xs.filter((x) => x % 2 === 0);"),
    "negyzetosszeg": ("negyzetosszeg", "n: number): number", "let s = 0;\n  for (let i = 1; i <= n; i++) s += i * i;\n  return s;"),
    "forditott": ("forditott", "s: string): string", "return [...s].reverse().join('');"),
    "max_index": ("maxIndex", "xs: number[]): number", "return xs.length ? xs.indexOf(Math.max(...xs)) : -1;"),
    "szamjegyosszeg": ("szamjegyosszeg", "n: number): number", "return [...String(Math.abs(n))].reduce((a, d) => a + Number(d), 0);"),
    "szavak_szama": ("szavakSzama", "s: string): number", "return s.split(/\\s+/).filter(Boolean).length;"),
    "celsius_fahrenheit": ("celsiusFahrenheit", "c: number): number", "return Math.round((c * 9 / 5 + 32) * 10) / 10;"),
    "egyedi": ("egyedi", "xs: number[]): number[]", "return [...new Set(xs)];"),
    "nagybetus_szavak": ("nagybetusSzavak", "s: string): string[]",
                         "return s.split(/\\s+/).filter((w) => w !== '' && w[0] !== w[0].toLowerCase());"),
    "atlag": ("atlag", "xs: number[]): number | null",
              "return xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 100) / 100 : null;"),
    "fizzbuzz": ("fizzbuzz", "n: number): string[]",
                 "return Array.from({ length: Math.max(0, n) }, (_, k) => {\n    const i = k + 1;\n"
                 "    return i % 15 === 0 ? 'FizzBuzz' : i % 3 === 0 ? 'Fizz' : i % 5 === 0 ? 'Buzz' : String(i);\n  });"),
    "szorzotabla": ("szorzotabla", "n: number): number[][]",
                    "const r = Array.from({ length: Math.max(0, n) }, (_, i) => i + 1);\n  return r.map((i) => r.map((j) => i * j));"),
    "palindrom": ("palindrom", "s: string): boolean",
                  "const t = [...s.toLowerCase()].filter((c) => /[\\p{L}\\p{N}]/u.test(c));\n  return t.join('') === [...t].reverse().join('');"),
    "romai_ertek": ("romaiErtek", "s: string): number",
                    "const V: Record<string, number> = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };\n"
                    "  const u = s.toUpperCase();\n  if (!u || [...u].some((c) => !(c in V))) throw new RangeError(s);\n"
                    "  let total = 0;\n  for (let i = 0; i < u.length; i++) {\n    const v = V[u[i]];\n"
                    "    total += i + 1 < u.length && V[u[i + 1]] > v ? -v : v;\n  }\n  return total;"),
    "romai_szam": ("romaiSzam", "n: number): string",
                   "if (!(n >= 1 && n <= 3999)) throw new RangeError(String(n));\n"
                   "  const P: [number, string][] = [[1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'],\n"
                   "    [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']];\n"
                   "  let out = '';\n  for (const [v, r] of P) while (n >= v) { out += r; n -= v; }\n  return out;"),
    "darabol": ("darabol<T>", "xs: T[], size: number): T[][]",
                "if (size < 1) throw new RangeError(String(size));\n  const out: T[][] = [];\n"
                "  for (let i = 0; i < xs.length; i += size) out.push(xs.slice(i, i + size));\n  return out;"),
    "kilapit": ("kilapit", "xs: unknown[]): unknown[]", "return xs.flat(Infinity);"),
    "rle_kodol": ("rleKodol", "s: string): string",
                  "let out = '';\n  const cs = [...s];\n  for (let i = 0; i < cs.length; ) {\n    let j = i;\n"
                  "    while (j < cs.length && cs[j] === cs[i]) j++;\n    out += `${j - i}${cs[i]}`;\n    i = j;\n  }\n  return out;"),
    "rle_dekodol": ("rleDekodol", "s: string): string",
                    "const parts = [...s.matchAll(/(\\d+)(\\D)/gu)];\n"
                    "  if (parts.map((m) => m[0]).join('') !== s || parts.some((m) => Number(m[1]) === 0)) throw new RangeError(s);\n"
                    "  return parts.map((m) => m[2].repeat(Number(m[1]))).join('');"),
    "osszefesul": ("osszefesul", "a: number[], b: number[]): number[]",
                   "const out: number[] = [];\n  let i = 0;\n  let j = 0;\n"
                   "  while (i < a.length && j < b.length) out.push(a[i] <= b[j] ? a[i++] : b[j++]);\n"
                   "  return [...out, ...a.slice(i), ...b.slice(j)];"),
    "binaris_kereses": ("binarisKereses", "xs: number[], x: number): number",
                        "let lo = 0;\n  let hi = xs.length;\n  while (lo < hi) {\n    const mid = (lo + hi) >> 1;\n"
                        "    if (xs[mid] < x) lo = mid + 1;\n    else hi = mid;\n  }\n  return lo < xs.length && xs[lo] === x ? lo : -1;"),
    "anagramma": ("anagramma", "a: string, b: string): boolean",
                  "const k = (s: string) => [...s.toLowerCase()].filter((c) => !/\\s/.test(c)).sort().join('');\n  return k(a) === k(b);"),
    "statisztika": ("statisztika", "s: string): { betu: number; szamjegy: number; szokoz: number; egyeb: number }",
                    "const d = { betu: 0, szamjegy: 0, szokoz: 0, egyeb: 0 };\n  for (const c of s) {\n"
                    "    if (/\\p{L}/u.test(c)) d.betu++;\n    else if (/\\p{Nd}/u.test(c)) d.szamjegy++;\n"
                    "    else if (/\\s/.test(c)) d.szokoz++;\n    else d.egyeb++;\n  }\n  return d;"),
    "camel_snake": ("camelSnake", "s: string): string",
                    "return [...s].map((c, i) => (i === 0 ? c.toLowerCase() : c !== c.toLowerCase() ? `_${c.toLowerCase()}` : c)).join('');"),
    "snake_camel": ("snakeCamel", "s: string): string",
                    "const p = s.split('_').filter(Boolean);\n  if (!p.length) return '';\n"
                    "  return p[0].toLowerCase() + p.slice(1).map((x) => x[0].toUpperCase() + x.slice(1).toLowerCase()).join('');"),
    "taj_ervenyes": ("tajErvenyes", "s: string): boolean",
                     "if (!/^(\\d{9}|\\d{3} \\d{3} \\d{3})$/.test(s)) return false;\n  const d = [...s.replaceAll(' ', '')].map(Number);\n"
                     "  return d.slice(0, 8).reduce((a, x, i) => a + x * (i % 2 === 0 ? 3 : 7), 0) % 10 === d[8];"),
    "idotartam_mp": ("idotartamMp", "s: string): number",
                     "const ORDER: Record<string, [number, number]> = { h: [0, 3600], m: [1, 60], s: [2, 1] };\n"
                     "  let total = 0;\n  let last = -1;\n  for (const part of s.split(' ')) {\n"
                     "    const m = /^(\\d+)([hms])$/.exec(part);\n    if (!m || ORDER[m[2]][0] <= last) throw new RangeError(s);\n"
                     "    last = ORDER[m[2]][0];\n    total += Number(m[1]) * ORDER[m[2]][1];\n  }\n  return total;"),
    "idotartam_szoveg": ("idotartamSzoveg", "mp: number): string",
                         "if (mp < 0) throw new RangeError(String(mp));\n  if (mp === 0) return '0 másodperc';\n"
                         "  const parts: [number, string][] = [[Math.floor(mp / 3600), 'óra'], [Math.floor((mp % 3600) / 60), 'perc'], [mp % 60, 'másodperc']];\n"
                         "  return parts.filter(([v]) => v).map(([v, n]) => `${v} ${n}`).join(' ');"),
    "hossz_szerint": ("hosszSzerint", "szavak: string[]): Record<number, string[]>",
                      "const d: Record<number, string[]> = {};\n  for (const w of szavak) (d[[...w].length] ??= []).push(w);\n  return d;"),
    "forgat": ("forgat<T>", "xs: T[], k: number): T[]",
               "const n = xs.length;\n  if (!n) return [];\n  const r = ((k % n) + n) % n;\n"
               "  return r ? [...xs.slice(n - r), ...xs.slice(0, n - r)] : [...xs];"),
    "pascal_sor": ("pascalSor", "n: number): number[]",
                   "if (n < 0) throw new RangeError(String(n));\n  let row = [1];\n"
                   "  for (let i = 0; i < n; i++) row = [0, ...row].map((a, j) => a + (row[j] ?? 0));\n  return row;"),
    "prim": ("prim", "n: number): boolean",
             "if (n < 2) return false;\n  for (let i = 2; i * i <= n; i++) if (n % i === 0) return false;\n  return true;"),
    "primek": ("primek", "n: number): number[]",
               "if (n < 2) return [];\n  const s = new Array<boolean>(n + 1).fill(true);\n  s[0] = s[1] = false;\n"
               "  for (let i = 2; i * i <= n; i++) if (s[i]) for (let j = i * i; j <= n; j += i) s[j] = false;\n"
               "  return s.flatMap((p, i) => (p ? [i] : []));"),
    "transzponal": ("transzponal", "m: number[][]): number[][]",
                    "if (m.some((r) => r.length !== m[0].length)) throw new RangeError('nem téglalap');\n"
                    "  return m.length ? m[0].map((_, j) => m.map((r) => r[j])) : [];"),
    "masodik_legnagyobb": ("masodikLegnagyobb", "xs: number[]): number | null",
                           "const u = [...new Set(xs)].sort((a, b) => a - b);\n  return u.length >= 2 ? u[u.length - 2] : null;"),
    "sortores": ("sortores", "szoveg: string, szelesseg: number): string[]",
                 "if (szelesseg < 1) throw new RangeError(String(szelesseg));\n  const sorok: string[] = [];\n  let cur = '';\n"
                 "  for (const w of szoveg.split(/\\s+/).filter(Boolean)) {\n"
                 "    if (cur && cur.length + 1 + w.length <= szelesseg) cur += ` ${w}`;\n"
                 "    else {\n      if (cur) sorok.push(cur);\n      cur = w;\n    }\n  }\n  if (cur) sorok.push(cur);\n  return sorok;"),
    "zarojelek": ("zarojelek", "s: string): boolean",
                  "const st: string[] = [];\n  const pair: Record<string, string> = { ')': '(', ']': '[', '}': '{' };\n"
                  "  for (const c of s) {\n    if ('([{'.includes(c)) st.push(c);\n"
                  "    else if (c in pair && st.pop() !== pair[c]) return false;\n  }\n  return st.length === 0;"),
    "telefonszam": ("telefonszam", "s: string): string",
                    "const m = /^(?:\\+36|36|06)(\\d{9})$/.exec(s.replace(/[ \\-/()]/g, ''));\n"
                    "  if (!m) throw new RangeError(s);\n  return `+36${m[1]}`;"),
    "datum": ("datum", "s: string): [number, number, number]",
              "const m = /^(\\d{4})\\. ?(\\d{1,2})\\. ?(\\d{1,2})\\.$/.exec(s);\n  if (!m) throw new RangeError(s);\n"
              "  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];\n"
              "  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);\n"
              "  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];\n"
              "  if (mo < 1 || mo > 12 || d < 1 || d > days[mo - 1]) throw new RangeError(s);\n  return [y, mo, d];"),
    "maganhangzok": ("maganhangzok", "s: string): number", "return [...s.toLowerCase()].filter((c) => 'aáeéiíoóöőuúüű'.includes(c)).length;"),
}
EXTRA = {
    "forgat": "test('forgat nem módosítja a bemenetet', () => {\n  const xs = [1, 2, 3];\n  forgat(xs, 1);\n"
              "  assert.deepEqual(xs, [1, 2, 3], 'forgat(xs, 1) után az xs változatlan');\n});\n",
    "primek": "test('primek(10000).length', () => assert.equal(primek(10000).length, 1229, 'primek(10000).length'));\n",
}
DROP_CASES = {"kilapit": lambda args: any(isinstance(x, tuple) for x in args[0])}  # tuples do not exist in JS

TEST_TMPL = """// {canary}
{header}import {{ test }} from 'node:test';
import assert from 'node:assert/strict';
import {{ {fn} }} from '../solution.ts';

const f = {fn} as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `{fn}(${{args.map((a) => JSON.stringify(a)).join(', ')}})`;
const CASES: [unknown[], unknown][] = {cases};
const ERRORS: unknown[][] = {errors};

for (const [args, want] of CASES) {{
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}}
for (const args of ERRORS) {{
  test(`hiba: ${{call(args)}}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}}
{extra}"""


def js(obj: object) -> str:
    def conv(o: object) -> object:
        if isinstance(o, tuple | list):
            return [conv(x) for x in o]
        if isinstance(o, dict):
            return {str(k): conv(v) for k, v in o.items()}
        return o
    return json.dumps(conv(obj), ensure_ascii=False)


def build() -> list[str]:
    counters = {0: 0, 1: 0}
    ids = []
    for level, pyname, topics, family, title, prompt, _sig, _ref, visible, hidden, errors, _extra, _ve in T:
        name, params, body = TS[pyname]
        fn = name.split("<")[0]
        counters[level] += 1
        tid = f"ts-l{level}-{counters[level]:04d}"
        canary = f"AURI-CANARY-{uuid.uuid5(NS, 'aurikod-hu-v1/' + tid)}"
        sig = f"export function {name}({params}"
        p = prompt.split("`", 2)
        text = p[0] + f"`{sig.removeprefix('export function ')}`" + p[2]  # the first code span is the signature
        for a, b in PROMPT_MAP:
            text = text.replace(a, b)
        bad = [w for w in FORBIDDEN if w in text]
        assert not bad, f"{tid}: python idiom left in prompt: {bad}"
        drop = DROP_CASES.get(pyname, lambda _a: False)
        vis = [(list(a), w) for a, w in visible if not drop(a)]
        hid = [(list(a), w) for a, w in hidden if not drop(a)]
        errs = [list(a) for a, _ in errors]
        d = ROOT / tid
        (d / "tests").mkdir(parents=True, exist_ok=True)
        (d / "ref").mkdir(exist_ok=True)
        yaml = (f"# {canary}\nid: {tid}\nlevel: {level}\nlang: ts\ntopics: [{', '.join(TOPIC.get(t, t) for t in topics)}]\n"
                f"title_hu: {title}\nprompt_hu: |\n"
                + textwrap.indent(textwrap.fill(text, 110, break_long_words=False, break_on_hyphens=False), "  ") + "\n"
                + f"signature: \"{sig}\"\nfiles: {{visible: tests/visible.test.ts, hidden: tests/hidden.test.ts, reference: ref/solution.ts}}\n"
                + "source: {kind: own, license: own}\nlimits: {wall_s: 20, mem_mb: 512}\nsplit: dev\n"
                + f"family: {family}\nrating: {1000 + 200 * level}\n")
        hidden_header = "// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.\n"
        files = {
            "task.yaml": yaml,
            "tests/visible.test.ts": TEST_TMPL.format(canary=canary, header="", fn=fn, cases=js(vis), errors="[]", extra=""),
            "tests/hidden.test.ts": TEST_TMPL.format(canary=canary, header=hidden_header, fn=fn, cases=js(hid), errors=js(errs),
                                                     extra=EXTRA.get(pyname, "")),
            "ref/solution.ts": f"// {canary}\n// Reference solution: only for validating the task.\n{sig} {{\n  {body}\n}}\n",
        }
        for rel, content in files.items():
            (d / rel).write_text(content, encoding="utf-8", newline="\n")
        ids.append(tid)
    return ids


if __name__ == "__main__":
    out = build()
    print(len(out), "tasks:", out[0], "…", out[-1])
