// secrets.ts — credentials and financial / official identifiers must never become
// long-term MEMORY (SECURITY.md §13.2, H-15). Memories are re-injected into future
// prompts (which may go to a hosted model), so a password typed once would otherwise
// travel with every later question. The chat transcript itself stays in the user's
// own account; only the memory / BRAIN layer is protected here.
//
//   containsSecret(text) — "don't learn from this at all" (chat turns, brain)
//   redactSecrets(text)  — keep the text, blank the secret VALUES (uploaded documents)
//
// Detection is about a disclosed VALUE, not about a topic:
//   • ordinary (often programming) talk must still be learned — "how do I hash
//     passwords?", `password: string;`, `user.password = hashed`,
//     `apiKey: process.env.OPENAI_API_KEY`, "the token limit is 4096";
//   • a value is a quoted literal, or a word containing a digit/symbol that is not a code
//     reference — "a jelszavam Kutya123", `"password": "s3cret!"`, `DB_PASSWORD=hunter2`;
//   • numbers are VALIDATED where a checksum exists (cards: Luhn, IBAN: mod-97, Hungarian
//     account numbers: giro check) so dates and ids that merely look similar pass.
//
// NOTE: JS `\b` is ASCII-only (it doesn't treat "ó" as a letter), so word edges use
// Unicode-aware look-arounds. A label may be preceded by "_" (DB_PASSWORD) or a quote.

// ── checksums ──────────────────────────────────────────────────────────────────
function luhn(digits: string): boolean {
  let sum = 0;
  let dbl = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let d = digits.charCodeAt(i) - 48;
    if (dbl) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
    dbl = !dbl;
  }
  return sum % 10 === 0;
}
/** IBAN ISO 13616 mod-97 check. */
function ibanOk(raw: string): boolean {
  const s = raw.replace(/\s+/g, '').toUpperCase();
  if (!/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(s)) return false;
  const moved = s.slice(4) + s.slice(0, 4);
  let rem = 0;
  for (const ch of moved) {
    const v = ch >= 'A' ? String(ch.charCodeAt(0) - 55) : ch;
    for (const d of v) rem = (rem * 10 + (d.charCodeAt(0) - 48)) % 97;
  }
  return rem === 1;
}
/** Hungarian giro account check: each block's digits weighted 9,7,3,1 sum to 0 mod 10. */
function huAccountOk(raw: string): boolean {
  const blocks = raw.split('-');
  const ok = (s: string) => [...s].reduce((sum, d, i) => sum + Number(d) * [9, 7, 3, 1][i % 4], 0) % 10 === 0;
  return ok(blocks[0]) && ok(blocks.slice(1).join(''));
}

// ── building blocks ────────────────────────────────────────────────────────────
const START = '(?<![\\p{L}\\p{N}])'; // "_" and quotes may precede a label (DB_PASSWORD, "password")
const END = '(?![\\p{L}\\p{N}])';
// Things that look like values but are code references, not secrets.
const NOT_REF =
  '(?!(?:process|os|import|env|window|globalThis|document|localStorage|sessionStorage|config|settings|this|self|req|res|request|response|data|user|form|input|props|state|ctx|context|args|params|options|opts|secrets?|vault|getenv|undefined|null|none|true|false)\\b)';
// A literal value: quoted, or an unquoted word with at least one digit or symbol.
const VALUE =
  `(?:"[^"\\s]{3,}"|'[^'\\s]{3,}'|${NOT_REF}(?=[^\\s,;"'()\\[\\]{}<>]*[\\d!@#$%^&*+=~?])[^\\s,;"'()\\[\\]{}<>]{3,})`;
const PW = 'password|passwd|passcode|jelszó|jelszo|jelszav\\p{L}*';
const GENERIC =
  'token|secret|api[ _-]?key|apikey|access[ _-]?key|client[ _-]?secret|private[ _-]?key|titkos kulcs\\p{L}*';

// Secret VALUES (all redactable). Each entry matches only the value, not the label.
const SECRET_VALUES: RegExp[] = [
  // key-shaped tokens: provider prefix + a long random body
  /\b(?:sk|pk|rk|gsk|sb_secret|ghp|gho|ghs|github_pat|xox[abprs]|auri_sk)[-_](?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{20,}/g,
  /\bAKIA[0-9A-Z]{16}\b/g, // AWS access key id
  /\bglpat-[A-Za-z0-9_-]{20,}/g, // GitLab
  /\bhf_[A-Za-z0-9]{30,}/g, // Hugging Face
  /\bnpm_[A-Za-z0-9]{36}\b/g, // npm
  /\bAIza[0-9A-Za-z_-]{30,}/g, // Google API key
  /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}/g, // JWT
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g, // PEM private key
  /(?<![\dA-Za-z#])\d{6}[A-Z]{2}(?![A-Za-z\d])/g, // Hungarian ID card number (123456AB) — not a #hex colour
  // labelled official ids (accented or not)
  new RegExp(`(?<=${START}(?:taj|taj-?szám\\p{L}*|tajszam\\p{L}*|tajszám\\p{L}*)\\P{N}{0,12})\\d{3}[ -]?\\d{3}[ -]?\\d{3}(?!\\d)`, 'giu'),
  new RegExp(`(?<=${START}(?:adóazonosító|adoazonosito|adószám|adoszam)\\p{L}*\\P{N}{0,12})\\d{8,11}(?:-\\d-\\d{2})?(?!\\d)`, 'giu'),
  new RegExp(`(?<=${START}(?:útlevél|utlevel)\\p{L}*\\s*[:=]?\\s*)[A-Z]{2}\\d{6,7}(?!\\d)`, 'giu'),
  // passwords: label (+ optional closing quote) then ':' / '=' / "is" / possessive, then a VALUE
  new RegExp(`(?<=${START}(?:${PW})["']?\\s*[:=]\\s*)${VALUE}`, 'giu'),
  new RegExp(`(?<=${START}(?:${PW})${END}\\s+(?:is\\s+|az\\s+|a\\s+)?)${VALUE}`, 'giu'),
  // PIN / CVV: digits only
  new RegExp(`(?<=${START}(?:pin(?:[ -]?(?:kód|kod|code))?(?:om|od|ja)?|cvv|cvc)${END}\\s*(?:is|az|a|:|=)?\\s*)\\d{3,8}(?!\\d)`, 'giu'),
  // generic secret labels: only with an explicit ':' or '=' and a long literal value
  new RegExp(
    `(?<=${START}(?:${GENERIC})["']?\\s*[:=]\\s*["']?)${NOT_REF}(?!\\$\\{)[^\\s,;"'()\\[\\]{}<>]{8,}`,
    'giu',
  ),
  // .env / shell style: NAME containing PASSWORD|SECRET|TOKEN|KEY…, '=', any literal value
  /(?<=^[ \t]*(?:export[ \t]+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_?KEY|CREDENTIALS?)[A-Z0-9_]*[ \t]*=[ \t]*["']?)(?!\$\{|\$\(|process\.)[^\s"'#]{6,}/gm,
];

// Number shapes confirmed by checksum (allow single spaces/tabs/dashes between groups).
const CARD = /(?<!\d)(?:\d[ \t-]{0,2}){12,18}\d(?!\d)/g;
const IBAN = /\b[A-Za-z]{2}\d{2}(?:[ \t]?[A-Za-z0-9]{4}){3,7}(?:[ \t]?[A-Za-z0-9]{1,4})?\b/g;
const HU_ACCOUNT = /(?<!\d)\d{8}-\d{8}(?:-\d{8})?(?!\d)/g;

function checked(text: string): string[] {
  const out: string[] = [];
  for (const m of text.match(CARD) ?? []) {
    const d = m.replace(/\D/g, '');
    if (d.length >= 13 && d.length <= 19 && luhn(d)) out.push(m);
  }
  for (const m of text.match(IBAN) ?? []) if (ibanOk(m)) out.push(m);
  for (const m of text.match(HU_ACCOUNT) ?? []) if (huAccountOk(m)) out.push(m);
  return out;
}

// Possessive disclosures of a secret, even when its value isn't recognisable by shape.
const DISCLOSURE = new RegExp(
  `${START}(?:(?:bank)?kártyaszámom|kartyaszamom|számlaszámom|szamlaszamom|taj-?számom|tajszámom|tajszamom|` +
    `adóazonosító(?:m|\\s+jelem)|adoazonosito(?:m|\\s+jelem)|személyim|szemelyim|` +
    `személyi\\s+igazolvány(?:om|szám(?:om)?)|útlevelem|utlevelem|útlevélszámom|` +
    `my\\s+(?:credit\\s+|debit\\s+)?card\\s+number|my\\s+iban|my\\s+social\\s+security(?:\\s+number)?)${END}`,
  'iu',
);

/** Does this text disclose a credential, card number or official / financial id? */
export function containsSecret(text: string): boolean {
  if (!text) return false;
  if (DISCLOSURE.test(text)) return true;
  if (checked(text).length) return true;
  return SECRET_VALUES.some((re) => {
    re.lastIndex = 0;
    const hit = re.test(text);
    re.lastIndex = 0;
    return hit;
  });
}

/** Replace every recognised secret value with "[REDACTED]" (keeps the rest). */
export function redactSecrets(text: string): string {
  if (!text) return text;
  let out = text;
  for (const c of checked(out)) out = out.split(c).join('[REDACTED]');
  for (const re of SECRET_VALUES) {
    re.lastIndex = 0;
    out = out.replace(re, '[REDACTED]');
  }
  return out;
}
