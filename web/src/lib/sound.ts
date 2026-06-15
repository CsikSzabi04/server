// Optional, opt-in sci-fi blips via WebAudio. Muted by default so it never
// surprises anyone. A single shared AudioContext, created lazily on first use.
let ctx: AudioContext | null = null;
let muted = true;

export function isMuted(): boolean {
  return muted;
}

export function setMuted(m: boolean): void {
  muted = m;
}

type Blip = 'type' | 'send' | 'recv' | 'error';

export function blip(kind: Blip = 'send'): void {
  if (muted) return;
  try {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    ctx ??= new Ctor();
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const freq = kind === 'send' ? 640 : kind === 'recv' ? 880 : kind === 'error' ? 180 : 520;
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, now);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.05, now + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.2);
  } catch {
    /* audio not available — ignore */
  }
}
