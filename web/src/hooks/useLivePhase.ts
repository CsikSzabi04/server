import { useEffect, useState } from 'react';
import { liveDurationMs } from '../lib/auriState';

/**
 * Drives the "is this text still alive?" phase.
 * Returns 'active' while streaming AND for liveDuration(charCount) afterwards,
 * then 'settled'. Because liveDuration grows with length, longer answers keep
 * pulsing/flickering longer before they calm down — the explicit requirement.
 */
export function useLivePhase(charCount: number, streaming: boolean): 'active' | 'settled' {
  const [phase, setPhase] = useState<'active' | 'settled'>('active');

  useEffect(() => {
    if (streaming) {
      setPhase('active');
      return;
    }
    setPhase('active');
    const t = setTimeout(() => setPhase('settled'), liveDurationMs(charCount));
    return () => clearTimeout(t);
  }, [streaming, charCount]);

  return phase;
}
