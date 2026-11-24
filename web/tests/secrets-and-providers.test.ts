// SECURITY regression tests:
//   • H-15 — secrets never become long-term memory (src/lib/secrets.ts, analyzeTurn)
//   • H-9  — Gemini's free quota is not used for EEA users (api/chat.ts, api/models.ts):
//            only with GEMINI_PAID=1 (billing-enabled project), per Google's terms.
// Lives outside src/ (not part of typecheck / build). Run from web/:
//   npx --yes tsx --test tests/secrets-and-providers.test.ts
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { containsSecret, redactSecrets } from '../src/lib/secrets';
import { analyzeTurn } from '../src/lib/memory';
import modelsHandler, { resetModelsCache } from '../api/models.js';

const SECRETS = [
  'a jelszavam Kutya123',
  'a jelszó: alma99',
  'my password is hunter2',
  'PIN: 4821',
  'kártyám 4111 1111 1111 1111',
  'HU42 1177 3016 1111 1018 0000 0000',
  'számla 11773016-11111018',
  'TAJ számom 123 456 789',
  'adóazonosító jelem: 8412345678',
  'személyim 123456AB',
  'key: gsk_abcdefghijklmnop1234',
  'AIzaSyA1234567890abcdefghijklmnopqrstu',
  'token: 9f8e7d6c5b4a39281706',
  'GROQ_API_KEY=gsk_live1234567890abcdef',
  'client_secret = "s3cr3tValue99xyz"',
  'a pin kódom 4821',
  'my credit card number ends in 4242',
  // review round 2: JSON, .env, more key shapes, unaccented HU, lowercase IBAN, passport
  '{"password": "Kutya123x"}',
  '{"apiKey": "abcd1234efgh5678"}',
  'DB_PASSWORD=supersecretvalue',
  'JWT_SECRET=0123456789abcdef',
  'AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
  'AKIAIOSFODNN7EXAMPLE',
  'glpat-abcdefghijklmnopqrstu',
  'jelszo: alma99',
  'adoazonosito: 8412345678',
  'password Kutya123',
  'the wifi password is Kutya2024',
  'hu42 1177 3016 1111 1018 0000 0000',
  'útlevélszám: BA1234567',
  'card\t4111\t1111\t1111\t1111',
];
// Ordinary talk — incl. everyday PROGRAMMING questions — must still be learned.
const NORMAL = [
  'Szabi vagyok, a CliMarkAI-n dolgozom',
  'szeretem a pizzát',
  'hogyan működik a React useState?',
  'a telefonom 2004-ben készült',
  'a kedvenc számom 42',
  'Budapesten lakom',
  'version 1.2.3 released 2026',
  'what is a JWT token?',
  'how do I hash passwords in Node with bcrypt?',
  'build a password reset flow with Supabase',
  'the token limit of the model is 4096',
  'store the secret in an environment variable',
  'pin this message please',
  'hogyan állítsak be jelszó-visszaállítást?',
  'API key rotation best practices',
  'Django pk_url_kwarg_for_lookup_view setting',
  // review round 2: code that only TALKS about credentials
  'password: string;',
  'user.password = hashed',
  'apiKey: process.env.OPENAI_API_KEY',
  'secret: process.env.JWT_SECRET',
  'token: localStorage.getItem("t")',
  'Your password must be at least 10 characters',
  'My password reset email never arrived',
  'A jelszavad legalább 10 karakter legyen',
  'enter the card number, expiry date and CVV fields',
  'color: #000000CC',
  'backup_20240101-20240131.tar',
  'pk_order_items_2024',
];

test('secrets are recognised (HU + EN), normal personal facts are not', () => {
  for (const s of SECRETS) assert.equal(containsSecret(s), true, `missed: ${s}`);
  for (const s of NORMAL) assert.equal(containsSecret(s), false, `false positive: ${s}`);
});

test('redaction keeps the text but blanks the secret value', () => {
  assert.equal(redactSecrets('a jelszavam Kutya123'), 'a jelszavam [REDACTED]');
  assert.equal(redactSecrets('kártyám 4111 1111 1111 1111'), 'kártyám [REDACTED]');
  assert.ok(!redactSecrets('GROQ_API_KEY=gsk_abcdefghijklmnop1234').includes('gsk_abc'));
  assert.equal(redactSecrets('szeretem a pizzát'), 'szeretem a pizzát');
});

test('a chat turn containing a secret teaches the memory nothing', () => {
  const a = analyzeTurn('Én vagyok Szabi, a jelszavam Kutya123', 'Rendben, megjegyeztem: Kutya123');
  assert.deepEqual(a.facts, []);
  assert.deepEqual(a.keywords, []);
  assert.equal(a.name, null);
  const b = analyzeTurn('Én vagyok Szabi és szeretem a pizzát', 'Szia Szabi!');
  assert.ok(b.facts.length > 0, 'ordinary personal facts are still learned');
});

function mkRes() {
  const r: any = { statusCode: 0, body: null, headers: {} };
  r.status = (c: number) => ((r.statusCode = c), r);
  r.json = (b: unknown) => ((r.body = b), r);
  r.setHeader = (k: string, v: string) => (r.headers[k.toLowerCase()] = v);
  return r;
}

test('Gemini is off unless the operator confirms a paid (billing-enabled) project', async () => {
  delete process.env.AURI_SERVER_URL;
  process.env.GEMINI_API_KEY = 'AIza-test';
  delete process.env.GEMINI_PAID;
  resetModelsCache();
  let res = mkRes();
  await modelsHandler({ method: 'GET', headers: {} } as any, res);
  assert.equal(res.body.hosted.gemini, null, 'free quota must not be offered (EEA users)');
  assert.equal(res.body.disabled.gemini, 'eea_paid_only', 'the picker can tell why');

  process.env.GEMINI_PAID = '1';
  resetModelsCache();
  res = mkRes();
  await modelsHandler({ method: 'GET', headers: {} } as any, res);
  assert.ok(res.body.hosted.gemini, 'paid project → Gemini available');
  assert.equal(res.body.disabled.gemini, undefined);
});
