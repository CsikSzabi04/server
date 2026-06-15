// Generates a strong secret API key, writes it into .env (creating .env from
// .env.example if needed) and prints it ONCE in a visible box.
//   Run with: npm run generate-key
import { randomBytes } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

function generateKey(): string {
  // auri_sk_ prefix (recognizable in logs, like Stripe's sk_) + 48 url-safe chars.
  return 'auri_sk_' + randomBytes(36).toString('base64url');
}

function upsertEnv(envPath: string, key: string, value: string): void {
  let content = '';
  if (existsSync(envPath)) content = readFileSync(envPath, 'utf8');

  const line = `${key}=${value}`;
  const re = new RegExp(`^${key}=.*$`, 'm');
  if (re.test(content)) {
    content = content.replace(re, line);
  } else {
    if (content.length && !content.endsWith('\n')) content += '\n';
    content += line + '\n';
  }
  writeFileSync(envPath, content, 'utf8');
}

// `string.length` counts UTF-16 units; precomposed accented chars are 1 unit,
// so this aligns fine for our (mostly ASCII) box content.
function box(lines: string[]): void {
  const width = Math.max(...lines.map((l) => l.length));
  const top = '╔' + '═'.repeat(width + 2) + '╗';
  const bottom = '╚' + '═'.repeat(width + 2) + '╝';
  console.log('\n' + top);
  for (const l of lines) console.log('║ ' + l.padEnd(width) + ' ║');
  console.log(bottom + '\n');
}

const cwd = process.cwd();
const envPath = resolve(cwd, '.env');
const examplePath = resolve(cwd, '.env.example');

// Seed .env from the example on first run so all other settings are present.
if (!existsSync(envPath) && existsSync(examplePath)) {
  writeFileSync(envPath, readFileSync(examplePath, 'utf8'), 'utf8');
}

const key = generateKey();
upsertEnv(envPath, 'AURI_API_KEY', key);

box([
  'AURI PRIVATE API KEY  (mentsd el — csak most latod teljesen!)',
  '',
  key,
  '',
  '-> Ezt masold a CliMark szerveroldali .env-jebe:',
  `   AURI_SERVER_API_KEY=${key}`,
]);

console.log(`A kulcs elmentve ide:  ${envPath}  (AURI_API_KEY)`);
console.log('Az .env gitignore-olva van — a kulcsot soha ne commitold/oszd meg publikusan.');
console.log('Ujrageneralashoz futtasd ujra: npm run generate-key\n');
