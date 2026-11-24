import { useEffect, useRef } from 'react';
import { useLivePhase } from '../hooks/useLivePhase';

interface Props {
  text: string;
  streaming: boolean;
}

// The "alive" text renderer.
//  - Each word mounts with a one-shot entrance animation (glow-in), so streamed
//    text appears word-by-word and lights up, then cools to the base color.
//  - While in the 'active' phase (streaming + liveDuration after) the whole
//    block breathes and a random word occasionally micro-flickers.
//  - Longer text => longer 'active' phase (see useLivePhase / liveDurationMs).
export default function LiveText({ text, streaming }: Props) {
  const phase = useLivePhase(text.length, streaming);
  const ref = useRef<HTMLDivElement>(null);

  // Random hologram-instability flicker — JS-driven (CSS can't random), and only
  // while active + motion allowed. Frequency scales a bit with length.
  useEffect(() => {
    if (phase !== 'active') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = ref.current;
    if (!el) return;

    const interval = Math.max(360, 760 - Math.min(400, text.length / 4));
    const id = window.setInterval(() => {
      const words = el.querySelectorAll<HTMLElement>('.live-word');
      if (!words.length) return;
      const target = words[Math.floor(Math.random() * words.length)];
      target.classList.add('flick');
      window.setTimeout(() => target.classList.remove('flick'), 240);
    }, interval);

    return () => window.clearInterval(id);
  }, [phase, text.length]);

  // Words + whitespace (whitespace incl. newlines preserved via CSS), with light
  // Markdown applied on the fly so **markers** never show while it streams.
  const tokens = liveTokens(text);

  return (
    <div ref={ref} className={`live-text ${phase === 'active' ? 'live-active' : 'live-settled'}`}>
      {tokens.map((tok, i) =>
        tok.ws ? (
          <span key={i} className="live-space">
            {tok.s}
          </span>
        ) : (
          <span key={i} className={`live-word${tok.line ? ` ${tok.line}` : ''}`}>
            {tok.parts.map((p, j) => (p.cls ? <span key={j} className={p.cls}>{p.s}</span> : p.s))}
          </span>
        ),
      )}
      {streaming && <span className="live-cursor" aria-hidden="true" />}
    </div>
  );
}

type LiveTok = { ws: true; s: string } | { ws: false; line: string; parts: { s: string; cls: string }[] };

/** Streaming-safe Markdown: per line, strip heading/quote/bullet syntax and toggle
 *  bold / italic / strike / `code` at the markers. Unclosed markers simply style
 *  the rest of the line until the closing one streams in. Fenced code lines are
 *  shown monospace (the fence lines themselves are hidden). */
function liveTokens(text: string): LiveTok[] {
  const out: LiveTok[] = [];
  let fence = false;
  const allLines = text.split('\n');
  allLines.forEach((raw, li) => {
    if (li > 0) out.push({ ws: true, s: '\n' });
    // A finished line only formats PAIRED '**' (so "**kwargs" stays literal); the line
    // still streaming in may have its closing '**' on the way, so it formats eagerly.
    const streamingLine = li === allLines.length - 1;
    const allowBold = streamingLine || (raw.match(/\*\*/g) ?? []).length % 2 === 0;
    if (/^\s*```/.test(raw)) {
      fence = !fence;
      return;
    }
    if (fence) {
      for (const t of raw.match(/\s+|\S+/g) ?? [])
        out.push(/^\s+$/.test(t) ? { ws: true, s: t } : { ws: false, line: 'lt-codeline', parts: [{ s: t, cls: '' }] });
      return;
    }
    let line = raw;
    let lineCls = '';
    let m: RegExpMatchArray | null;
    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {
      out.push({ ws: false, line: 'lt-hr', parts: [{ s: '────────', cls: '' }] });
      return;
    }
    if ((m = line.match(/^\s{0,3}#{1,6}\s+/))) {
      line = line.slice(m[0].length);
      lineCls = 'lt-h';
    } else if ((m = line.match(/^\s{0,3}>\s?/))) {
      line = line.slice(m[0].length);
      lineCls = 'lt-quote';
    } else if ((m = line.match(/^(\s*)[-*+•]\s+/))) {
      if (m[1]) out.push({ ws: true, s: m[1] });
      out.push({ ws: false, line: '', parts: [{ s: m[1] ? '◦' : '•', cls: 'lt-bullet' }] }, { ws: true, s: ' ' });
      line = line.slice(m[0].length);
    }
    let bold = false;
    let ital = false;
    let strike = false;
    let code = false;
    // Italic only with single '*', and only if the line has a closing one: code-ish prose
    // like "*args, **kwargs" or "_private_var" must not italicise the rest of the line.
    const singles = (line.replace(/\*\*/g, '').match(/\*/g) ?? []).length;
    const allowItal = singles >= 2 && singles % 2 === 0;
    const cls = () =>
      [code ? 'lt-code' : '', bold ? 'lt-b' : '', ital ? 'lt-i' : '', strike ? 'lt-s' : ''].filter(Boolean).join(' ');
    for (const tok of line.match(/\s+|\S+/g) ?? []) {
      if (/^\s+$/.test(tok)) {
        out.push({ ws: true, s: tok });
        continue;
      }
      const parts: { s: string; cls: string }[] = [];
      const segs = tok.split(/(\*\*|~~|`)/).filter((x) => x !== '');
      segs.forEach((seg, si) => {
        if (seg === '`') {
          code = !code;
          return;
        }
        if (!code && seg === '**') {
          if (allowBold) bold = !bold;
          else parts.push({ s: '**', cls: cls() }); // unpaired on a finished line → literal
          return;
        }
        if (!code && seg === '~~') {
          strike = !strike;
          return;
        }
        let s = seg;
        let closeItal = false;
        if (allowItal && !code && si === 0 && /^\*[^*\s]/.test(s)) {
          ital = true;
          s = s.slice(1);
        }
        if (allowItal && !code && si === segs.length - 1 && ital && /[^*\s]\*[.,;:!?)]*$/.test(s)) {
          s = s.replace(/\*([.,;:!?)]*)$/, '$1');
          closeItal = true;
        }
        if (s) parts.push({ s, cls: cls() });
        if (closeItal) ital = false;
      });
      if (parts.length) out.push({ ws: false, line: lineCls, parts });
    }
  });
  return out;
}
