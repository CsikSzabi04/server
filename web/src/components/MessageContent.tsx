import { useState } from 'react';
import LiveText from './LiveText';

// Renders an assistant reply: prose stays plain, fenced ```code``` blocks become
// formatted, copy-able code cards (programmer-oriented answers actually read well).
// While streaming, the raw text keeps its live typewriter (content is still
// changing); once finished, it re-renders with code blocks.

interface Part {
  code?: string;
  lang?: string;
  text?: string;
}

/** Split text into prose segments + fenced ```code``` blocks. */
function parseParts(text: string): Part[] {
  const parts: Part[] = [];
  const re = /```([a-zA-Z0-9.+#-]*)\n?([\s\S]*?)```/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) });
    parts.push({ lang: m[1] || '', code: m[2].replace(/\n+$/, '') });
    last = re.lastIndex;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
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
  if (parts.length === 1 && parts[0].text !== undefined) {
    return <span className="msg-prose">{parts[0].text}</span>;
  }
  return (
    <>
      {parts.map((p, i) =>
        p.code !== undefined ? (
          <CodeBlock key={i} lang={p.lang ?? ''} code={p.code} />
        ) : p.text?.trim() ? (
          <span key={i} className="msg-prose">
            {p.text}
          </span>
        ) : null,
      )}
    </>
  );
}
