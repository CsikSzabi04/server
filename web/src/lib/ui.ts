import type { CSSProperties } from 'react';

/** Lets us pass CSS custom properties (--foo) through React's `style` prop. */
export function cssVars(vars: Record<string, string | number>): CSSProperties {
  return vars as unknown as CSSProperties;
}

/** Deterministic-ish pseudo telemetry string for HUD decoration. */
export function hex(n: number, len = 2): string {
  return n.toString(16).toUpperCase().padStart(len, '0');
}
