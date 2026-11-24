import { useMemo, type ReactNode } from 'react';

// Small, dependency-free Markdown renderer for assistant replies. Builds React
// elements directly (never innerHTML), so model output can't inject markup.
// Covers what chat models actually emit: **bold**, *italic*, `code`, ~~strike~~,
// [links](https://…), bare URLs, # headings, - / 1. lists (nested by indent),
// > quotes, --- rules and | tables |. Fenced ```code``` is handled upstream
// (MessageContent → CodeBlock), so this only ever sees prose.

// ── inline ─────────────────────────────────────────────────────────────────────
// Named groups (order = priority): code · ***bold italic*** · **bold** / __bold__ ·
// ~~strike~~ · [link](url) · *italic* / _italic_ · bare url.
// URLs may contain BALANCED parentheses (e.g. https://en.wikipedia.org/wiki/Mars_(planet)).
const URL_BODY = String.raw`(?:[^\s<>()"']|\([^\s<>()"']*\))*(?:[^\s<>()"'.,;:!?]|\([^\s<>()"']*\))`;
const INLINE = new RegExp(
  [
    String.raw`(?<tick>` + '`' + String.raw`+)(?<code>[^` + '`' + String.raw`\n]+?)\k<tick>(?!` + '`' + ')',
    String.raw`\*\*\*(?=\S)(?<bi>[^\n]*?\S)\*\*\*`,
    String.raw`\*\*(?=\S)(?<b1>[^\n]*?\S)\*\*`,
    String.raw`(?<!\w)__(?=\S)(?<b2>[^\n]*?\S)__(?!\w)`,
    String.raw`~~(?=\S)(?<s>[^\n]*?\S)~~`,
    String.raw`\[(?<lt>[^\]\n]+)\]\((?<lu>https?:\/\/(?:[^\s()]|\([^\s()]*\))+)\)`,
    String.raw`(?<![\w*])\*(?=[^\s*])(?<i1>[^*\n]*?[^\s*])\*(?![\w*])`,
    String.raw`(?<![\w_])_(?=[^\s_])(?<i2>[^_\n]*?[^\s_])_(?![\w_])`,
    String.raw`(?<url>https?:\/\/` + URL_BODY + ')',
  ].join('|'),
  'g',
);

/** Inline Markdown → React nodes. `inLink` = we're inside a link's text, so no nested
 *  <a> may be produced (e.g. [https://x.y](https://x.y) — invalid DOM otherwise). */
export function renderInline(s: string, k = 'i', inLink = false): ReactNode[] {
  const out: ReactNode[] = [];
  const re = new RegExp(INLINE.source, 'g');
  let last = 0;
  let n = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    const g = m.groups ?? {};
    if (m.index > last) out.push(s.slice(last, m.index));
    const key = `${k}.${n++}`;
    if (g.code !== undefined) out.push(<code key={key} className="md-code">{g.code}</code>);
    else if (g.bi !== undefined)
      out.push(
        <strong key={key}>
          <em>{renderInline(g.bi, key, inLink)}</em>
        </strong>,
      );
    else if (g.b1 !== undefined || g.b2 !== undefined)
      out.push(<strong key={key}>{renderInline(g.b1 ?? g.b2, key, inLink)}</strong>);
    else if (g.s !== undefined) out.push(<del key={key}>{renderInline(g.s, key, inLink)}</del>);
    else if (g.lt !== undefined)
      out.push(
        inLink ? (
          <span key={key}>{renderInline(g.lt, key, true)}</span>
        ) : (
          <a key={key} className="md-link" href={g.lu} target="_blank" rel="noreferrer noopener">
            {renderInline(g.lt, key, true)}
          </a>
        ),
      );
    else if (g.i1 !== undefined || g.i2 !== undefined)
      out.push(<em key={key}>{renderInline(g.i1 ?? g.i2, key, inLink)}</em>);
    else if (g.url !== undefined)
      out.push(
        inLink ? (
          g.url
        ) : (
          <a key={key} className="md-link" href={g.url} target="_blank" rel="noreferrer noopener">
            {g.url}
          </a>
        ),
      );
    last = re.lastIndex;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

// ── blocks ─────────────────────────────────────────────────────────────────────
interface ListItem {
  ordered: boolean;
  num: string;
  depth: number;
  text: string;
}
type Align = 'left' | 'center' | 'right' | undefined;
type Block =
  | { t: 'p'; lines: string[] }
  | { t: 'h'; level: number; text: string }
  | { t: 'list'; items: ListItem[] }
  | { t: 'quote'; lines: string[] }
  | { t: 'hr' }
  | { t: 'table'; head: string[]; align: Align[]; rows: string[][] };

const HR = /^\s{0,3}([-*_])(\s*\1){2,}\s*$/;
// A closing "#" run only counts when separated by whitespace ("## Learn C#" keeps its #).
const HEAD = /^\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/;
const UL = /^(\s*)[-*+•]\s+(.*)$/;
const OL = /^(\s*)(\d{1,3})[.)]\s+(.*)$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;
const TSEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

/** Split a table row on `|` — but not on an escaped `\|`, and not inside a `code` span
 *  (models write `string | null` or `a || b` in table cells). */
function splitRow(l: string): string[] {
  let s = l.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|') && !s.endsWith('\\|')) s = s.slice(0, -1);
  const cells: string[] = [];
  let cur = '';
  let inCode = false;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === '\\' && s[i + 1] === '|') {
      cur += '|';
      i++;
      continue;
    }
    if (ch === '`') inCode = !inCode;
    if (ch === '|' && !inCode) {
      cells.push(cur.trim());
      cur = '';
      continue;
    }
    cur += ch;
  }
  cells.push(cur.trim());
  return cells;
}
const depthOf = (indent: string): number => Math.min(3, Math.floor(indent.replace(/\t/g, '  ').length / 2));

export function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const blocks: Block[] = [];
  let para: string[] | null = null;
  let prevBlank = false;
  const flush = () => {
    if (para && para.length) blocks.push({ t: 'p', lines: para });
    para = null;
  };
  const top = () => blocks[blocks.length - 1];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) {
      flush();
      prevBlank = true;
      continue;
    }
    let m: RegExpMatchArray | null;
    if (HR.test(line)) {
      flush();
      blocks.push({ t: 'hr' });
    } else if ((m = line.match(HEAD))) {
      flush();
      blocks.push({ t: 'h', level: m[1].length, text: m[2] });
    } else if (
      line.includes('|') &&
      i + 1 < lines.length &&
      TSEP.test(lines[i + 1]) &&
      lines[i + 1].includes('|') && // a bare "---" under a line with "|" is a rule, not a table
      lines[i + 1].includes('-')
    ) {
      flush();
      const head = splitRow(line);
      const align: Align[] = splitRow(lines[i + 1]).map((c) =>
        c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : c.startsWith(':') ? 'left' : undefined,
      );
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(splitRow(lines[i++]));
      i--;
      blocks.push({ t: 'table', head, align, rows });
    } else if ((m = line.match(UL)) || (m = line.match(OL))) {
      flush();
      const ordered = m.length === 4;
      const item: ListItem = ordered
        ? { ordered, num: m[2], depth: depthOf(m[1]), text: m[3] }
        : { ordered, num: '', depth: depthOf(m[1]), text: m[2] };
      const t = top();
      if (t && t.t === 'list') t.items.push(item);
      else blocks.push({ t: 'list', items: [item] });
    } else if ((m = line.match(QUOTE))) {
      flush();
      const t = top();
      if (t && t.t === 'quote' && !prevBlank) t.lines.push(m[1]);
      else blocks.push({ t: 'quote', lines: [m[1]] });
    } else {
      const t = top();
      if (!para && !prevBlank && t && t.t === 'list') {
        // lazy continuation of the previous list item
        const it = t.items[t.items.length - 1];
        it.text += ` ${line.trim()}`;
      } else {
        (para ??= []).push(line);
      }
    }
    prevBlank = false;
  }
  flush();
  return blocks;
}

function renderBlock(b: Block, i: number): ReactNode {
  const k = `b${i}`;
  switch (b.t) {
    case 'p':
      return (
        <p key={k} className="md-p">
          {b.lines.map((l, j) => (
            <span key={j}>
              {j > 0 && <br />}
              {renderInline(l, `${k}.${j}`)}
            </span>
          ))}
        </p>
      );
    case 'h':
      return (
        <div key={k} className={`md-h md-h${Math.min(b.level, 4)}`} role="heading" aria-level={b.level}>
          {renderInline(b.text, k)}
        </div>
      );
    case 'hr':
      return <hr key={k} className="md-hr" />;
    case 'quote':
      return (
        <blockquote key={k} className="md-quote">
          {b.lines.map((l, j) => (
            <span key={j}>
              {j > 0 && <br />}
              {renderInline(l, `${k}.${j}`)}
            </span>
          ))}
        </blockquote>
      );
    case 'list':
      return (
        <ul key={k} className="md-list">
          {b.items.map((it, j) => (
            <li key={j} className={`md-li${it.ordered ? ' is-num' : ''}`} style={{ marginLeft: `${it.depth * 1.3}em` }}>
              <span className="md-mark" aria-hidden="true">
                {it.ordered ? `${it.num}.` : it.depth ? '◦' : '•'}
              </span>
              <span className="md-li-body">{renderInline(it.text, `${k}.${j}`)}</span>
            </li>
          ))}
        </ul>
      );
    case 'table':
      return (
        <div key={k} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {b.head.map((c, j) => (
                  <th key={j} style={{ textAlign: b.align[j] }}>
                    {renderInline(c, `${k}.h${j}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.rows.map((r, ri) => (
                <tr key={ri}>
                  {b.head.map((_, j) => (
                    <td key={j} style={{ textAlign: b.align[j] }}>
                      {renderInline(r[j] ?? '', `${k}.${ri}.${j}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
  }
}

export default function Markdown({ text }: { text: string }) {
  const blocks = useMemo(() => parseBlocks(text), [text]);
  return <div className="md">{blocks.map(renderBlock)}</div>;
}
