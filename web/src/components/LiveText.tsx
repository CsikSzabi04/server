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

  // Split into words + whitespace; whitespace (incl. newlines) preserved via CSS.
  const tokens = text.match(/\s+|\S+/g) ?? [];

  return (
    <div ref={ref} className={`live-text ${phase === 'active' ? 'live-active' : 'live-settled'}`}>
      {tokens.map((tok, i) =>
        /^\s+$/.test(tok) ? (
          <span key={i} className="live-space">
            {tok}
          </span>
        ) : (
          <span key={i} className="live-word">
            {tok}
          </span>
        ),
      )}
      {streaming && <span className="live-cursor" aria-hidden="true" />}
    </div>
  );
}
