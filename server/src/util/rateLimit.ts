// Minimal in-memory fixed-window rate limiter, keyed by API key (falling back
// to IP). Good enough for a single-instance private server; swap for Redis if
// you ever run multiple replicas.
import type { Request, Response, NextFunction } from 'express';
import { config } from '../config';

interface Bucket {
  count: number;
  resetAt: number;
}

const buckets = new Map<string, Bucket>();

// Periodically drop expired buckets so the map doesn't grow unbounded.
setInterval(() => {
  const now = Date.now();
  for (const [key, b] of buckets) {
    if (now >= b.resetAt) buckets.delete(key);
  }
}, 60_000).unref();

export function rateLimit(req: Request, res: Response, next: NextFunction): void {
  if (config.rateLimitPerMin <= 0) {
    next();
    return;
  }

  const key = req.apiKeyMask || req.ip || 'unknown';
  const now = Date.now();

  let b = buckets.get(key);
  if (!b || now >= b.resetAt) {
    b = { count: 0, resetAt: now + 60_000 };
    buckets.set(key, b);
  }
  b.count += 1;

  const remaining = Math.max(0, config.rateLimitPerMin - b.count);
  res.setHeader('X-RateLimit-Limit', String(config.rateLimitPerMin));
  res.setHeader('X-RateLimit-Remaining', String(remaining));

  if (b.count > config.rateLimitPerMin) {
    const retryAfter = Math.ceil((b.resetAt - now) / 1000);
    res.setHeader('Retry-After', String(retryAfter));
    res.status(429).json({ error: 'rate_limited', retry_after: retryAfter });
    return;
  }

  next();
}
