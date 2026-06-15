// Tiny structured logger. Always masks API keys; never logs prompt bodies
// unless LOG_PROMPTS is explicitly enabled (see chat route).

/**
 * Mask a secret for logs: keeps the recognizable prefix + last 4 chars.
 *   auri_sk_a1b2...wxyz  ->  auri_sk_****wxyz
 */
export function maskKey(key: string | undefined | null): string {
  if (!key) return '(none)';
  const last4 = key.slice(-4);
  if (key.startsWith('auri_sk_')) return `auri_sk_****${last4}`;
  return `****${last4}`;
}

function ts(): string {
  return new Date().toISOString();
}

function fmt(level: string, msg: string, meta?: Record<string, unknown>): string {
  const tail = meta && Object.keys(meta).length ? ' ' + JSON.stringify(meta) : '';
  return `[${ts()}] ${level.padEnd(5)} ${msg}${tail}`;
}

export const logger = {
  info(msg: string, meta?: Record<string, unknown>) {
    console.log(fmt('INFO', msg, meta));
  },
  warn(msg: string, meta?: Record<string, unknown>) {
    console.warn(fmt('WARN', msg, meta));
  },
  error(msg: string, meta?: Record<string, unknown>) {
    console.error(fmt('ERROR', msg, meta));
  },
};
