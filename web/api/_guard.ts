// _guard.ts — shared front door for the serverless proxies (/api/chat, /api/search,
// /api/tts). The leading underscore keeps Vercel from exposing it as an endpoint.
// SECURITY.md §8 (H-1, H-2, H-12):
//
//   1. method   — POST only.
//   2. origin   — a browser Origin must be this deployment (same host) or listed in
//                 ALLOWED_ORIGINS; other sites can't spend our keys from their pages.
//   3. caller   — a signed-in user is identified from their Supabase access token
//                 (verified against Supabase, cached briefly); everyone else is a
//                 guest, identified by IP. AURI_REQUIRE_LOGIN=1 rejects guests.
//   4. limits   — per caller, per endpoint: requests / minute and / day; guests get
//                 tighter limits. In-memory per warm instance = best effort (a burst
//                 spread across many cold instances can exceed it); for strict global
//                 limits back this with a shared store (Upstash / Vercel KV).
//   5. no-store — responses carry personal content → never cached by a CDN/proxy.
//
// Never logs tokens, prompts or queries; only the endpoint, caller kind and reason.
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { createHash } from 'node:crypto';
import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

export type Endpoint = 'chat' | 'search' | 'tts' | 'models' | 'pre';
export interface Caller {
  kind: 'user' | 'guest';
  /** Supabase user id (users) or client IP (guests). Never logged in full. */
  id: string;
}

// ── limits (env-overridable, e.g. LIMIT_CHAT_USER_MIN=30) ───────────────────────
const DEFAULTS: Record<Endpoint, { user: [number, number]; guest: [number, number] }> = {
  //            [per minute, per day]
  chat: { user: [20, 500], guest: [8, 80] },
  search: { user: [30, 600], guest: [10, 120] },
  tts: { user: [120, 4000], guest: [40, 600] }, // TTS is called once per sentence
  models: { user: [30, 2000], guest: [20, 1000] }, // model-picker availability probe (GET)
  // per-IP pre-limit BEFORE any token verification, so random bearer tokens can't be
  // used to make us hammer Supabase (amplification)
  pre: { user: [240, 20000], guest: [240, 20000] },
};
function limitsFor(ep: Endpoint, kind: Caller['kind']): [number, number] {
  const env = (s: string) => Number(process.env[`LIMIT_${ep.toUpperCase()}_${kind.toUpperCase()}_${s}`]);
  const [m, d] = DEFAULTS[ep][kind];
  return [env('MIN') > 0 ? env('MIN') : m, env('DAY') > 0 ? env('DAY') : d];
}

// ── helpers ────────────────────────────────────────────────────────────────────
const sha = (s: string): string => createHash('sha256').update(s).digest('hex');
const header = (req: VercelRequest, name: string): string => {
  const v = req.headers[name];
  return (Array.isArray(v) ? v[0] : v) ?? '';
};

/** Client IP as set by the Vercel edge (which overwrites client-sent values). */
export function clientIp(req: VercelRequest): string {
  return (
    header(req, 'x-real-ip') ||
    header(req, 'x-forwarded-for').split(',')[0].trim() ||
    req.socket?.remoteAddress ||
    'unknown'
  );
}

/** Rate-limit key for a guest: the IPv4 address, or the IPv6 /64 network (one
 *  subscriber usually owns a whole /64, so per-address keys would be trivial to rotate). */
export function guestKey(ip: string): string {
  if (isIP(ip) !== 6) return ip;
  const h = hextets(ip);
  return h ? `${h.slice(0, 4).map((x) => x.toString(16)).join(':')}::/64` : ip;
}

/** Is this browser Origin allowed to call us? (Absent Origin = non-browser client.) */
export function originAllowed(req: VercelRequest): boolean {
  const origin = header(req, 'origin');
  if (!origin) return true;
  let host = '';
  try {
    host = new URL(origin).host.toLowerCase();
  } catch {
    return false;
  }
  if (host === header(req, 'host').toLowerCase()) return true; // same deployment
  const allowed = (process.env.ALLOWED_ORIGINS ?? '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (allowed.includes(origin.toLowerCase())) return true;
  // local development hosts, never in production
  if (process.env.VERCEL_ENV !== 'production' && /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return true;
  return false;
}

// ── caller identification (Supabase access token → user id) ───────────────────
const TOKEN_TTL_MS = 60_000;
const tokenCache = new Map<string, { uid: string | null; until: number }>(); // sha(token) → uid

async function userIdFromToken(token: string): Promise<string | null> {
  const key = sha(token);
  const hit = tokenCache.get(key);
  if (hit && hit.until > Date.now()) return hit.uid;
  const url = (process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/+$/, '');
  const anon = process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || '';
  let uid: string | null = null;
  if (url && anon) {
    try {
      const r = await fetch(`${url}/auth/v1/user`, {
        headers: { apikey: anon, authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(3000),
      });
      if (r.ok) {
        const u = (await r.json()) as { id?: unknown };
        uid = typeof u.id === 'string' ? u.id : null;
      }
    } catch {
      uid = null; // Supabase unreachable → treat as guest (stricter limits), never as a user
    }
  }
  evictOldest(tokenCache, 2000);
  tokenCache.set(key, { uid, until: Date.now() + TOKEN_TTL_MS });
  return uid;
}

/** Memory bound without wiping everyone's state: drop the OLDEST 10% (Map keeps
 *  insertion order) once a map reaches `max` entries. */
function evictOldest<K, V>(m: Map<K, V>, max: number): void {
  if (m.size < max) return;
  let n = Math.ceil(max / 10);
  for (const k of m.keys()) {
    m.delete(k);
    if (--n <= 0) break;
  }
}

export async function identify(req: VercelRequest): Promise<Caller> {
  const auth = header(req, 'authorization');
  const m = auth.match(/^Bearer\s+(.+)$/i);
  const token = m?.[1]?.trim();
  if (token && token.length < 4096) {
    const uid = await userIdFromToken(token);
    if (uid) return { kind: 'user', id: uid };
  }
  return { kind: 'guest', id: guestKey(clientIp(req)) };
}

// ── rate limiting (fixed windows, in memory) ───────────────────────────────────
interface Bucket {
  minStart: number;
  min: number;
  dayStart: number;
  day: number;
}
const buckets = new Map<string, Bucket>();

/** Count one request; returns seconds to wait if over the limit, else 0. */
export function hit(ep: Endpoint, caller: Caller, now = Date.now()): number {
  const [perMin, perDay] = limitsFor(ep, caller.kind);
  const key = `${ep}:${caller.kind}:${sha(caller.id)}`;
  let b = buckets.get(key);
  if (!b) {
    evictOldest(buckets, 20_000); // memory bound (oldest first — not everyone's counters)
    b = { minStart: now, min: 0, dayStart: now, day: 0 };
    buckets.set(key, b);
  }
  if (now - b.minStart >= 60_000) {
    b.minStart = now;
    b.min = 0;
  }
  if (now - b.dayStart >= 86_400_000) {
    b.dayStart = now;
    b.day = 0;
  }
  if (b.day >= perDay) return Math.ceil((b.dayStart + 86_400_000 - now) / 1000);
  if (b.min >= perMin) return Math.ceil((b.minStart + 60_000 - now) / 1000);
  b.min++;
  b.day++;
  return 0;
}

/** Test hook: forget all counters. */
export function resetLimits(): void {
  buckets.clear();
  tokenCache.clear();
}

/**
 * Run all checks. Returns the caller when the request may proceed; otherwise it has
 * already sent the error response and returns null.
 */
export async function guard(
  req: VercelRequest,
  res: VercelResponse,
  ep: Exclude<Endpoint, 'pre'>,
  method: 'POST' | 'GET' = 'POST',
): Promise<Caller | null> {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  // CORS only for the explicit ALLOWED_ORIGINS list (same-origin needs none).
  const origin = header(req, 'origin');
  const listed = (process.env.ALLOWED_ORIGINS ?? '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (origin && listed.includes(origin.toLowerCase())) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Methods', `${method}, OPTIONS`);
    res.setHeader('Access-Control-Allow-Headers', 'content-type, authorization');
    res.setHeader('Vary', 'Origin');
    if (req.method === 'OPTIONS') {
      res.status(204).end();
      return null;
    }
  }
  if (req.method !== method) {
    res.status(405).json({ error: 'method_not_allowed' });
    return null;
  }
  if (!originAllowed(req)) {
    console.warn(`[guard] ${ep}: blocked foreign origin`);
    res.status(403).json({ error: 'forbidden_origin' });
    return null;
  }
  // Cheap per-IP pre-limit FIRST: a flood of random bearer tokens must not turn into a
  // flood of Supabase look-ups.
  const preWait = hit('pre', { kind: 'guest', id: guestKey(clientIp(req)) });
  if (preWait > 0) {
    res.setHeader('Retry-After', String(preWait));
    res.status(429).json({ error: 'rate_limited', message: 'Too many requests.', retryAfter: preWait });
    return null;
  }
  const caller = await identify(req);
  if (caller.kind === 'guest' && process.env.AURI_REQUIRE_LOGIN === '1') {
    res.status(401).json({ error: 'login_required', message: 'Please sign in to use Auri.' });
    return null;
  }
  const wait = hit(ep, caller);
  if (wait > 0) {
    console.warn(`[guard] ${ep}: rate limit (${caller.kind})`);
    res.setHeader('Retry-After', String(wait));
    res.status(429).json({
      error: 'rate_limited',
      message:
        caller.kind === 'guest'
          ? 'Too many requests. Please wait a bit — or sign in for a higher limit.'
          : 'Too many requests. Please wait a bit.',
      retryAfter: wait,
    });
    return null;
  }
  return caller;
}

// ── chat input validation ──────────────────────────────────────────────────────
export const MAX_MESSAGES = 100;
export const MAX_PROMPT_CHARS = 120_000;
const ROLES = new Set(['system', 'user', 'assistant']);

export interface ChatMsg {
  role: 'system' | 'user' | 'assistant';
  content: string;
  /** user turns only: data:image/(png|jpeg|webp|gif);base64 URLs (validated below) */
  images?: string[];
}

// Images (vision): a few compressed screenshots, well under Vercel's ~4.5 MB body limit.
export const MAX_IMAGES = 4;
const MAX_IMAGE_CHARS = 1_500_000;
const MAX_IMAGES_TOTAL_CHARS = 4_000_000;
const IMAGE_DATA_URL = /^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/]+=*$/;

/** Keep only well-formed messages with an allowed role; enforce count + size. */
export function validateMessages(raw: unknown): { ok: true; messages: ChatMsg[] } | { ok: false; error: string } {
  if (!Array.isArray(raw) || raw.length === 0) return { ok: false, error: 'messages required' };
  if (raw.length > MAX_MESSAGES) return { ok: false, error: `too many messages (max ${MAX_MESSAGES})` };
  const out: ChatMsg[] = [];
  let total = 0;
  let imageCount = 0;
  let imageChars = 0;
  for (const m of raw) {
    if (!m || typeof m !== 'object') return { ok: false, error: 'invalid message' };
    const { role, content, images } = m as Record<string, unknown>;
    if (typeof role !== 'string' || !ROLES.has(role)) return { ok: false, error: 'invalid role' };
    if (typeof content !== 'string') return { ok: false, error: 'invalid content' };
    total += content.length;
    const msg: ChatMsg = { role: role as ChatMsg['role'], content };
    if (images !== undefined) {
      if (role !== 'user' || !Array.isArray(images)) return { ok: false, error: 'invalid images' };
      for (const img of images) {
        if (typeof img !== 'string' || img.length > MAX_IMAGE_CHARS || !IMAGE_DATA_URL.test(img))
          return { ok: false, error: 'invalid image (png/jpeg/webp/gif data URL, max 1.5 MB)' };
        imageCount++;
        imageChars += img.length;
      }
      if (images.length) msg.images = images as string[];
    }
    out.push(msg);
  }
  if (imageCount > MAX_IMAGES) return { ok: false, error: `too many images (max ${MAX_IMAGES})` };
  if (imageChars > MAX_IMAGES_TOTAL_CHARS) return { ok: false, error: 'images too large' };
  if (total > MAX_PROMPT_CHARS) return { ok: false, error: `prompt too large (max ${MAX_PROMPT_CHARS} chars)` };
  return { ok: true, messages: out };
}

export const clamp = (n: unknown, lo: number, hi: number): number | undefined =>
  typeof n === 'number' && Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : undefined;

// ── SSRF protection for server-side page fetches (/api/search) ─────────────────
function privateV4(ip: string): boolean {
  const [a, b] = ip.split('.').map(Number);
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    (a === 100 && b >= 64 && b <= 127) || // carrier-grade NAT
    (a === 169 && b === 254) || // link-local / cloud metadata
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 192 && b === 0) || // 192.0.0.0/24 + 192.0.2.0/24 (IETF / docs)
    (a === 198 && (b === 18 || b === 19)) ||
    a >= 224 // multicast / reserved
  );
}

/** IPv6 → its 8 hextets (handles "::" and a dotted IPv4 tail). null if malformed. */
function hextets(ip: string): number[] | null {
  let s = ip.toLowerCase().split('%')[0]; // drop a zone id
  const dotted = s.match(/(\d{1,3}(?:\.\d{1,3}){3})$/);
  if (dotted) {
    const p = dotted[1].split('.').map(Number);
    if (p.some((x) => x > 255)) return null;
    s = s.slice(0, -dotted[1].length) + ((p[0] << 8) | p[1]).toString(16) + ':' + ((p[2] << 8) | p[3]).toString(16);
  }
  const halves = s.split('::');
  if (halves.length > 2) return null;
  const head = halves[0] ? halves[0].split(':') : [];
  const tail = halves.length === 2 && halves[1] ? halves[1].split(':') : [];
  const fill = halves.length === 2 ? 8 - head.length - tail.length : 0;
  if (fill < 0 || (halves.length === 1 && head.length !== 8)) return null;
  const all = [...head, ...Array(fill).fill('0'), ...tail];
  if (all.length !== 8 || all.some((h) => !/^[0-9a-f]{1,4}$/.test(h))) return null;
  return all.map((h) => parseInt(h, 16));
}
const v4of = (hi: number, lo: number): string => `${hi >> 8}.${hi & 255}.${lo >> 8}.${lo & 255}`;

/** Private / internal / special address? IPv4 and IPv6 — including IPv6 forms that
 *  EMBED an IPv4 address (::ffff:a.b.c.d mapped, ::a.b.c.d compatible, 64:ff9b::/96
 *  NAT64, 2002::/16 6to4), which the URL parser writes in hex (e.g. [::ffff:7f00:1]). */
function privateIp(ip: string): boolean {
  if (isIP(ip) === 4) return privateV4(ip);
  const h = hextets(ip);
  if (!h) return true; // unparseable → refuse
  const zero5 = h[0] === 0 && h[1] === 0 && h[2] === 0 && h[3] === 0 && h[4] === 0;
  if (zero5 && h[5] === 0xffff) return privateV4(v4of(h[6], h[7])); // ::ffff:0:0/96 mapped
  if (zero5 && h[5] === 0) return h[6] === 0 && h[7] <= 1 ? true : privateV4(v4of(h[6], h[7])); // ::, ::1, ::a.b.c.d
  if (h[0] === 0x64 && h[1] === 0xff9b) return privateV4(v4of(h[6], h[7])); // NAT64
  if (h[0] === 0x2002) return privateV4(v4of(h[1], h[2])); // 6to4
  if (h[0] === 0x2001 && h[1] === 0) return true; // Teredo
  if (h[0] === 0x2001 && h[1] === 0x0db8) return true; // documentation
  if ((h[0] & 0xfe00) === 0xfc00) return true; // fc00::/7 unique local
  if ((h[0] & 0xffc0) === 0xfe80) return true; // fe80::/10 link-local
  if ((h[0] & 0xffc0) === 0xfec0) return true; // fec0::/10 site-local (deprecated)
  if ((h[0] & 0xff00) === 0xff00) return true; // ff00::/8 multicast
  return false;
}

/** May the server fetch this URL? Public http(s) hosts only (DNS-resolved). */
export async function publicUrl(raw: string): Promise<boolean> {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return false;
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
  if (u.username || u.password) return false;
  if (u.port && u.port !== '80' && u.port !== '443') return false;
  const host = u.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!host || host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.internal') || host.endsWith('.local'))
    return false;
  if (isIP(host)) return !privateIp(host);
  try {
    const addrs = await lookup(host, { all: true });
    return addrs.length > 0 && addrs.every((a) => !privateIp(a.address));
  } catch {
    return false;
  }
}

/** fetch() that re-checks every redirect hop against publicUrl (max 3 hops). */
export async function safeFetch(url: string, init: RequestInit & { signal?: AbortSignal }): Promise<Response | null> {
  let current = url;
  for (let hop = 0; hop < 4; hop++) {
    if (!(await publicUrl(current))) return null;
    const r = await fetch(current, { ...init, redirect: 'manual' });
    if (r.status >= 300 && r.status < 400) {
      const loc = r.headers.get('location');
      if (!loc) return null;
      current = new URL(loc, current).toString();
      continue;
    }
    return r;
  }
  return null;
}
