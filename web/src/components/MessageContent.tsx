import { useState } from 'react';
import LiveText from './LiveText';
import Markdown from './Markdown';

// Renders an assistant reply: prose is rendered as Markdown (bold, lists,
// headings, tables, links…), fenced ```code``` blocks become formatted, copy-able
// code cards. While streaming, the live typewriter keeps going (with light inline
// formatting); once finished, it re-renders as full Markdown + code blocks.

interface Part {
  code?: string;
  lang?: string;
  text?: string;
}

/** First word of a fence's info string: ```js title="a.js" → "js". */
const langOf = (info: string): string => info.trim().split(/\s+/)[0] ?? '';

/** Split text into prose segments + fenced ```code``` blocks. */
function parseParts(text: string): Part[] {
  const parts: Part[] = [];
  // group 1: info string (rest of the fence line), group 2: the newline (absent for a
  // one-line ```code``` span), group 3: the code
  const re = /```([^\n`]*)(\n?)([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    if (m[2]) parts.push({ lang: langOf(m[1]), code: m[3].replace(/\n+$/, '') });
    else parts.push({ lang: '', code: (m[1] + m[3]).trim() }); // one-line fence: all of it is code
    last = re.lastIndex;
  }
  let rest = text.slice(last);
  // A reply cut off inside a code block (max_tokens, network drop) has an UNCLOSED fence:
  // show what follows it as code, not as Markdown prose (# comments would become headings).
  const open = rest.indexOf('```');
  if (open >= 0) {
    if (open > 0) parts.push({ text: rest.slice(0, open) });
    const after = rest.slice(open + 3);
    const nl = after.indexOf('\n');
    parts.push(nl >= 0 ? { lang: langOf(after.slice(0, nl)), code: after.slice(nl + 1).replace(/\n+$/, '') } : { lang: '', code: after });
    rest = '';
  }
  if (rest) parts.push({ text: rest });
  return parts.length ? parts : [{ text }];
}

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard
      ?.writeText(code)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      })
      .catch(() => {
        /* clipboard blocked */
      });
  };
  return (
    <div className="msg-code">
      <div className="msg-code-bar">
        <span className="msg-code-lang">{lang || 'code'}</span>
        <button className="msg-code-copy" onClick={copy}>
          {copied ? 'copied ✓' : '⧉ copy'}
        </button>
      </div>
      <pre className="msg-code-pre">{code}</pre>
    </div>
  );
}

export default function MessageContent({ text, streaming }: { text: string; streaming: boolean }) {
  if (streaming) return <LiveText text={text} streaming />;
  const parts = parseParts(text);
  return (
    <>
      {parts.map((p, i) =>
        p.code !== undefined ? (
          <CodeBlock key={i} lang={p.lang ?? ''} code={p.code} />
        ) : p.text?.trim() ? (
          <Markdown key={i} text={p.text} />
        ) : null,
      )}
    </>
  );
}
