// SECURITY regression tests for the serverless proxy (api/_guard.ts + api/chat.ts):
// SECURITY.md §8 — H-1 (who is calling), H-2 (rate + size limits), H-12 (SSRF).
// No network: fetch is stubbed. Lives outside src/ (not part of typecheck / build).
// Run from web/:   npx --yes tsx --test tests/proxy-guard.test.ts
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  originAllowed,
  identify,
  hit,
  resetLimits,
  validateMessages,
  publicUrl,
  MAX_MESSAGES,
} from '../api/_guard.js';
import chatHandler from '../api/chat.js';
import { fitHistory } from '../src/lib/history';

// ── tiny Vercel req/res doubles ─────────────────────────────────────────────────
type Headers = Record<string, string>;
function mkReq(opts: { method?: string; headers?: Headers; body?: unknown } = {}) {
  return {
    method: opts.method ?? 'POST',
    headers: { host: 'auri.example', 'x-real-ip': '203.0.113.7', ...(opts.headers ?? {}) },
    body: opts.body ?? {},
    query: {},
    socket: { remoteAddress: '203.0.113.7' },
  } as any;
}
function mkRes() {
  const r: any = {
    statusCode: 200,
    headers: {} as Headers,
    body: undefined as unknown,
    headersSent: false,
    status(c: number) {
      r.statusCode = c;
      return r;
    },
    setHeader(k: string, v: string) {
      r.headers[k.toLowerCase()] = v;
    },
    json(b: unknown) {
      r.body = b;
      r.headersSent = true;
      return r;
    },
    send(b: unknown) {
      r.body = b;
      r.headersSent = true;
      return r;
    },
    write() {
      r.headersSent = true;
    },
    end() {
      r.headersSent = true;
    },
    on() {},
  };
  return r;
}

// ── fetch stub: Supabase /auth/v1/user + the local Ollama server ───────────────
const realFetch = globalThis.fetch;
let forwarded: any = null;
globalThis.fetch = (async (input: any, init?: any) => {
  const url = String(input);
  if (url.endsWith('/auth/v1/user')) {
    const auth = init?.headers?.authorization ?? '';
    return auth === 'Bearer good-token'
      ? new Response(JSON.stringify({ id: 'user-123' }), { status: 200 })
      : new Response('{}', { status: 401 });
  }
  if (url.endsWith('/health')) return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
  if (url.endsWith('/v1/chat')) {
    forwarded = JSON.parse(init.body);
    return new Response(JSON.stringify({ reply: 'hi', model: 'local' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }
  return realFetch(input, init);
}) as typeof fetch;

process.env.SUPABASE_URL = 'https://proj.supabase.example';
process.env.SUPABASE_ANON_KEY = 'anon';
process.env.VERCEL_ENV = 'production';

beforeEach(() => {
  resetLimits();
  forwarded = null;
  delete process.env.AURI_REQUIRE_LOGIN;
  delete process.env.ALLOWED_ORIGINS;
  delete process.env.AURI_SERVER_URL;
  delete process.env.AURI_SERVER_API_KEY;
});

const okBody = { messages: [{ role: 'user', content: 'hello' }], stream: false };

test('origin: own deployment and non-browser callers pass, other sites are blocked', () => {
  assert.equal(originAllowed(mkReq()), true, 'no Origin header (curl / server)');
  assert.equal(originAllowed(mkReq({ headers: { origin: 'https://auri.example' } })), true, 'same host');
  assert.equal(originAllowed(mkReq({ headers: { origin: 'https://evil.example' } })), false, 'foreign site');
  assert.equal(originAllowed(mkReq({ headers: { origin: 'http://localhost:5173' } })), false, 'no localhost in production');
  process.env.ALLOWED_ORIGINS = 'https://partner.example';
  assert.equal(originAllowed(mkReq({ headers: { origin: 'https://partner.example' } })), true, 'explicit allow-list');
});

test('caller: a valid Supabase token = that user; anything else = guest by IP', async () => {
  assert.deepEqual(await identify(mkReq({ headers: { authorization: 'Bearer good-token' } })), {
    kind: 'user',
    id: 'user-123',
  });
  assert.deepEqual(await identify(mkReq({ headers: { authorization: 'Bearer forged' } })), {
    kind: 'guest',
    id: '203.0.113.7',
  });
  assert.deepEqual(await identify(mkReq()), { kind: 'guest', id: '203.0.113.7' });
});

test('rate limit: guests are capped per minute, users get more, callers are separate', () => {
  const guest = { kind: 'guest' as const, id: '198.51.100.1' };
  for (let i = 0; i < 8; i++) assert.equal(hit('chat', guest), 0, `guest request ${i + 1} allowed`);
  assert.ok(hit('chat', guest) > 0, '9th guest request in a minute is refused');
  assert.equal(hit('chat', { kind: 'guest', id: '198.51.100.2' }), 0, 'another guest has its own budget');
  const user = { kind: 'user' as const, id: 'u1' };
  for (let i = 0; i < 20; i++) assert.equal(hit('chat', user), 0);
  assert.ok(hit('chat', user) > 0, 'users are capped too (21st in a minute)');
  assert.equal(hit('search', guest), 0, 'budgets are per endpoint');
});

test('validation: only system/user/assistant, bounded count and size', () => {
  assert.equal(validateMessages([{ role: 'user', content: 'x' }]).ok, true);
  assert.equal(validateMessages([]).ok, false);
  assert.equal(validateMessages([{ role: 'tool', content: 'x' }]).ok, false, 'unknown role');
  assert.equal(validateMessages([{ role: 'user', content: 42 }]).ok, false, 'non-string content');
  assert.equal(validateMessages(Array(MAX_MESSAGES + 1).fill({ role: 'user', content: 'x' })).ok, false);
  assert.equal(validateMessages([{ role: 'user', content: 'x'.repeat(200_000) }]).ok, false, 'too large');
});

test('SSRF: internal, metadata and non-http targets are never fetched', async () => {
  for (const bad of [
    'http://127.0.0.1/admin',
    'http://10.0.0.5/',
    'http://192.168.1.1/',
    'http://169.254.169.254/latest/meta-data/',
    'http://[::1]/',
    'http://localhost:3000/',
    'file:///etc/passwd',
    'http://user:pw@1.1.1.1/',
    'http://1.1.1.1:6379/',
  ])
    assert.equal(await publicUrl(bad), false, bad);
  assert.equal(await publicUrl('https://1.1.1.1/'), true, 'a public address is fine');
});

test('/api/chat: method, origin and login-required are enforced', async () => {
  let res = mkRes();
  await chatHandler(mkReq({ method: 'GET' }), res);
  assert.equal(res.statusCode, 405);

  res = mkRes();
  await chatHandler(mkReq({ headers: { origin: 'https://evil.example' }, body: okBody }), res);
  assert.equal(res.statusCode, 403);

  process.env.AURI_REQUIRE_LOGIN = '1';
  res = mkRes();
  await chatHandler(mkReq({ body: okBody }), res);
  assert.equal(res.statusCode, 401, 'guest refused when login is required');
});

test('/api/chat: bad roles are rejected and guests hit 429 after their budget', async () => {
  let res = mkRes();
  await chatHandler(mkReq({ body: { messages: [{ role: 'admin', content: 'x' }] } }), res);
  assert.equal(res.statusCode, 400);

  resetLimits();
  for (let i = 0; i < 8; i++) {
    res = mkRes();
    await chatHandler(mkReq({ body: okBody }), res);
    assert.notEqual(res.statusCode, 429);
  }
  res = mkRes();
  await chatHandler(mkReq({ body: okBody }), res);
  assert.equal(res.statusCode, 429);
  assert.ok(Number(res.headers['retry-after']) > 0, 'Retry-After is set');
});

test('/api/chat: only validated fields reach the local server; responses are no-store', async () => {
  process.env.AURI_SERVER_URL = 'https://tunnel.example';
  process.env.AURI_SERVER_API_KEY = 'k';
  const res = mkRes();
  await chatHandler(
    mkReq({
      headers: { authorization: 'Bearer good-token' },
      body: {
        ...okBody,
        max_tokens: 999_999,
        temperature: 9,
        user_id: 'someone-else',
        evil: { $where: 'x' },
      },
    }),
    res,
  );
  assert.equal(res.statusCode, 200);
  assert.equal(res.headers['cache-control'], 'no-store');
  assert.ok(forwarded, 'request was forwarded to the local server');
  assert.deepEqual(Object.keys(forwarded).sort(), ['max_tokens', 'messages', 'stream', 'temperature']);
  assert.equal(forwarded.max_tokens, 4096, 'max_tokens clamped');
  assert.equal(forwarded.temperature, 2, 'temperature clamped');
});

test('a very long chat is trimmed client-side so the guard still accepts it', () => {
  const sys = [
    { role: 'system' as const, content: 'persona '.repeat(200) },
    { role: 'system' as const, content: 'memory '.repeat(300) },
  ];
  const turns = Array.from({ length: 300 }, (_, i) => ({
    role: (i % 2 === 0 ? 'user' : 'assistant') as 'user' | 'assistant',
    content: `turn ${i} `.repeat(120),
  }));
  turns.push({ role: 'user', content: 'the NEWEST question' });
  assert.equal(validateMessages([...sys, ...turns]).ok, false, 'untrimmed: rejected by the guard');
  const fitted = fitHistory([...sys, ...turns]);
  assert.equal(validateMessages(fitted).ok, true, 'trimmed: accepted');
  assert.equal(fitted[0].content, sys[0].content, 'system messages are kept');
  assert.equal(fitted[fitted.length - 1].content, 'the NEWEST question', 'the newest message is kept whole');
  assert.notEqual(fitted[2].role, 'assistant', 'the window does not open on a dangling reply');
});

test('SSRF: IPv6 forms that embed or alias internal addresses are refused', async () => {
  for (const bad of [
    'http://[::ffff:127.0.0.1]/', // written by the URL parser as [::ffff:7f00:1]
    'http://[::ffff:7f00:1]/',
    'http://[::ffff:a9fe:a9fe]/latest/meta-data/', // 169.254.169.254
    'http://[::ffff:a00:1]/', // 10.0.0.1
    'http://[::7f00:1]/', // IPv4-compatible 127.0.0.1
    'http://[64:ff9b::a9fe:a9fe]/', // NAT64 → metadata
    'http://[2002:7f00:1::1]/', // 6to4 → 127.0.0.1
    'http://[fe90::1]/', // link-local (fe80::/10)
    'http://[fec0::1]/', // site-local
    'http://[fd12:3456::1]/', // unique local
    'http://[::]/',
  ])
    assert.equal(await publicUrl(bad), false, bad);
  assert.equal(await publicUrl('http://[2606:4700:4700::1111]/'), true, 'a public IPv6 address is fine');
  assert.equal(await publicUrl('http://[::ffff:1.1.1.1]/'), true, 'a mapped PUBLIC IPv4 is fine');
});
