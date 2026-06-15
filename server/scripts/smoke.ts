// Smoke test: exercises the main endpoints against a RUNNING server.
//   1) start the server in another terminal:  npm run dev
//   2) run:                                    npm run smoke
// Override target with SMOKE_URL=... (defaults to http://localhost:$PORT).
import 'dotenv/config';

const base = (process.env.SMOKE_URL ?? `http://localhost:${process.env.PORT ?? '8787'}`).replace(/\/+$/, '');
const key = (process.env.AURI_API_KEY ?? '').split(',')[0].trim();

let pass = 0;
let fail = 0;

function check(name: string, cond: boolean, detail?: string): void {
  if (cond) {
    pass++;
    console.log(`  ✓ ${name}`);
  } else {
    fail++;
    console.log(`  ✗ ${name}${detail ? ' — ' + detail : ''}`);
  }
}

async function main(): Promise<void> {
  console.log(`\nSmoke test against ${base}\n`);

  // 1) Public health
  try {
    const r = await fetch(`${base}/health`);
    const j: any = await r.json();
    check('GET /health -> 200', r.status === 200, `status=${r.status}`);
    check('health has model field', Boolean(j.model), JSON.stringify(j));
    console.log('    health:', JSON.stringify(j));
  } catch (e) {
    check('GET /health reachable', false, String(e));
    console.log('    Is the server running? Start it with `npm run dev`.');
  }

  // 2) Missing key -> 401
  try {
    const r = await fetch(`${base}/v1/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ messages: [{ role: 'user', content: 'hi' }] }),
    });
    check('POST /v1/chat without key -> 401', r.status === 401, `got ${r.status}`);
  } catch (e) {
    check('401 (no key) reachable', false, String(e));
  }

  // 3) Wrong key -> 401
  try {
    const r = await fetch(`${base}/v1/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer wrong-key' },
      body: JSON.stringify({ messages: [{ role: 'user', content: 'hi' }] }),
    });
    check('POST /v1/chat wrong key -> 401', r.status === 401, `got ${r.status}`);
  } catch (e) {
    check('401 (wrong key) reachable', false, String(e));
  }

  if (!key) {
    console.log('\n  (no AURI_API_KEY in .env — skipping authorized tests; run `npm run generate-key`)');
  } else {
    // 4) Empty messages -> 400
    try {
      const r = await fetch(`${base}/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify({ messages: [] }),
      });
      check('empty messages -> 400', r.status === 400, `got ${r.status}`);
    } catch (e) {
      check('validation reachable', false, String(e));
    }

    // 5) Real chat (needs Ollama). 503/400 tolerated if Ollama/model is missing.
    try {
      const r = await fetch(`${base}/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Reply with the single word: OK' }],
          max_tokens: 20,
        }),
      });
      const j: any = await r.json().catch(() => ({}));
      if (r.status === 200) {
        check('authorized chat -> 200 with reply', typeof j.reply === 'string' && j.reply.length > 0);
        check('usage present', Boolean(j.usage), JSON.stringify(j.usage));
        console.log('    reply:', JSON.stringify(j.reply).slice(0, 160));
      } else {
        console.log(`    chat returned ${r.status}: ${JSON.stringify(j)}`);
        console.log('    -> OK if Ollama is not installed/running yet (see README).');
      }
    } catch (e) {
      check('chat reachable', false, String(e));
    }

    // 6) Streaming (needs Ollama). Best-effort.
    try {
      const r = await fetch(`${base}/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'Count: 1 2 3' }],
          stream: true,
          max_tokens: 20,
        }),
      });
      if (r.status === 200 && r.headers.get('content-type')?.includes('text/event-stream')) {
        const text = await r.text();
        check('stream ends with [DONE]', text.includes('data: [DONE]'), text.slice(-80));
      } else {
        console.log(`    stream returned ${r.status} (Ollama likely not running) — skipped`);
      }
    } catch (e) {
      console.log('    stream test skipped:', String(e));
    }
  }

  console.log(`\nResult: ${pass} passed, ${fail} failed.\n`);
  // Set exitCode instead of calling process.exit(): forcing exit while undici
  // keep-alive sockets / abort timers are mid-close can trip a libuv assertion
  // on Windows. Letting the loop drain naturally avoids that.
  process.exitCode = fail > 0 ? 1 : 0;
}

void main();
