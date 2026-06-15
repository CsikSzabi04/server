// Central visual state machine. Every animated element (reactor, widgets, frame
// glow) reacts to this single state, which keeps the whole HUD coherent.
export type AuriState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

export interface StatePalette {
  /** Primary accent color for the state. */
  accent: string;
  /** Glow color. */
  glow: string;
  /** Relative reactor spin speed multiplier. */
  speed: number;
  /** Human-readable status shown in the HUD. */
  label: string;
}

export const STATE_PALETTE: Record<AuriState, StatePalette> = {
  idle: { accent: '#1fe5ff', glow: 'rgba(31,229,255,0.55)', speed: 1, label: 'STANDBY' },
  listening: { accent: '#35c8e8', glow: 'rgba(53,200,232,0.8)', speed: 1.6, label: 'LISTENING' },
  thinking: { accent: '#ff9d2f', glow: 'rgba(255,157,47,0.85)', speed: 2.6, label: 'PROCESSING' },
  speaking: { accent: '#1fe5ff', glow: 'rgba(31,229,255,0.95)', speed: 2.0, label: 'TRANSMITTING' },
  error: { accent: '#ff4d4d', glow: 'rgba(255,77,77,0.9)', speed: 0.6, label: 'UPLINK LOST' },
};

/**
 * How long the freshly-arrived text keeps "living" (active flicker/wave) before
 * it settles into the quiet idle-glow. Scales with length — the explicit
 * requirement: longer answers stay alive longer.
 */
export function liveDurationMs(charCount: number): number {
  const base = 1400;
  const perChar = 9;
  const min = 1400;
  const max = 14_000;
  return Math.min(max, Math.max(min, base + charCount * perChar));
}
