import { createHash, timingSafeEqual } from 'node:crypto';
import type { Request, Response, NextFunction } from 'express';
import { config } from './config';
import { maskKey } from './util/logger';

// Augment Express request with the (masked) key used, for rate-limiting + logs.
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      apiKeyMask?: string;
    }
  }
}

function sha256(s: string): Buffer {
  return createHash('sha256').update(s, 'utf8').digest();
}

// Pre-hash valid keys once. We compare fixed-length (32 byte) digests so that
// timingSafeEqual never throws on length mismatch and comparison stays constant
// time regardless of how wrong the supplied key is.
let cachedHashes: Buffer[] | null = null;
function validHashes(): Buffer[] {
  if (!cachedHashes) cachedHashes = config.apiKeys.map(sha256);
  return cachedHashes;
}

function extractKey(req: Request): string | null {
  const auth = req.header('authorization');
  if (auth && auth.toLowerCase().startsWith('bearer ')) {
    return auth.slice(7).trim();
  }
  const x = req.header('x-api-key');
  if (x) return x.trim();
  return null;
}

/**
 * Express middleware enforcing the secret API key.
 * Accepts either `Authorization: Bearer <key>` or `x-api-key: <key>`.
 * Returns a deliberately vague 401 on any failure (no detail leakage).
 */
export function requireApiKey(req: Request, res: Response, next: NextFunction): void {
  const provided = extractKey(req);
  if (!provided) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  const providedHash = sha256(provided);
  let ok = false;
  for (const h of validHashes()) {
    // h and providedHash are both 32 bytes -> safe & constant time.
    if (timingSafeEqual(h, providedHash)) ok = true;
  }

  if (!ok) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  req.apiKeyMask = maskKey(provided);
  next();
}
