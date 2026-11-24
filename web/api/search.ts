// Vercel serverless web search for the BRAIN's web-learning path (BRAIN_BUILD §5.b).
// KEYLESS by default: scrapes DuckDuckGo's HTML endpoint server-side (no API key,
// no CORS issues for the browser). Returns a compact list of {title, url, snippet}.
// The browser calls this same-origin via /api/search; nothing secret is exposed.
//
// (Optional upgrade later: set SEARCH_API=brave|tavily + the key, server-side only.)
import type { VercelRequest, VercelResponse } from '@vercel/node';
// Caller identification, rate limits, origin check + SSRF-safe fetching (SECURITY.md §8).
import { guard, safeFetch } from './_guard.js';

interface WebHit {
  title: string;
  url: string;
  snippet: string;
}

function clean(s: string): string {
  return s
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// DDG wraps result links in //duckduckgo.com/l/?uddg=<encoded-real-url>
function realUrl(href: string): string {
  const m = href.match(/[?&]uddg=([^&]+)/);
  if (m) {
    try {
      return decodeURIComponent(m[1]);
    } catch {
      return '';
    }
  }
  if (href.startsWith('//')) return `https:${href}`;
  return href.startsWith('http') ? href : '';
}

// Strip a full HTML page down to readable text: drop script/style/head/nav/footer
// blocks (and their contents) + comments first, then remaining tags + entities.
// The client distils this further with AI-4's extractKeyContent (query-relevant).
function htmlToText(html: string): string {
  return clean(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<head[\s\S]*?<\/head>/gi, ' ')
      .replace(/<!--[\s\S]*?-->/g, ' ')
      .replace(/<(nav|footer|header|aside|form)[\s\S]*?<\/\1>/gi, ' '),
  );
}

/** Best-effort: fetch a result page and return cleaned text (never throws). */
async function fetchPageText(url: string): Promise<string> {
  try {
    // SSRF guard: public http(s) hosts only, every redirect hop re-checked.
    const r = await safeFetch(url, {
      headers: { 'user-agent': 'Mozilla/5.0 (compatible; AuriBrain/1)' },
      signal: AbortSignal.timeout(7000),
    });
    if (!r || !r.ok) return '';
    const ct = r.headers.get('content-type') ?? '';
    if (!/text\/html|text\/plain|xml/i.test(ct)) return '';
    return htmlToText(await r.text()).slice(0, 4000);
  } catch {
    return '';
  }
}

async function ddgSearch(query: string, max = 6): Promise<WebHit[]> {
  const res = await fetch('https://html.duckduckgo.com/html/', {
    method: 'POST',
    headers: {
      'content-type': 'application/x-www-form-urlencoded',
      'user-agent': 'Mozilla/5.0 (compatible; AuriBrain/1)',
    },
    body: `q=${encodeURIComponent(query)}`,
    signal: AbortSignal.timeout(9000),
  });
  if (!res.ok) return [];
  const html = await res.text();

  const snippets: string[] = [];
  const snipRe = /<a[^>]*class="result__snippet"[^>]*>([\s\S]*?)<\/a>/g;
  let sm: RegExpExecArray | null;
  while ((sm = snipRe.exec(html))) snippets.push(clean(sm[1]));

  const hits: WebHit[] = [];
  const linkRe = /<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = linkRe.exec(html)) && hits.length < max) {
    const url = realUrl(m[1]);
    const title = clean(m[2]);
    if (url && title) hits.push({ title, url, snippet: snippets[i] ?? '' });
    i++;
  }
  return hits;
}

export default async function handler(req: VercelRequest, res: VercelResponse): Promise<void> {
  // POST only, own origin, caller identified, within rate limits — else already answered.
  if (!(await guard(req, res, 'search'))) return;

  const body = (req.body && typeof req.body === 'object' ? req.body : {}) as Record<string, unknown>;
  const query = (typeof body.query === 'string' && body.query) || (typeof body.q === 'string' && body.q) || '';

  if (!query || typeof query !== 'string') {
    res.status(400).json({ error: 'query required' });
    return;
  }

  const pagesWanted = Math.max(0, Math.min(3, Number(body.pages) || 0));

  try {
    const results = await ddgSearch(query.slice(0, 256));
    let pages: string[] = [];
    if (pagesWanted > 0 && results.length) {
      pages = (
        await Promise.all(results.slice(0, pagesWanted).map((h) => fetchPageText(h.url)))
      ).filter((t) => t.length > 80);
    }
    res.status(200).json({ results, pages });
  } catch (e) {
    // Never hard-fail the chat: return empty so the pipeline falls back to the model.
    // The reason goes to the server log only (no query text), never to the client.
    console.warn(`[search] failed: ${(e as Error).message}`);
    res.status(200).json({ results: [], pages: [], error: 'search_failed' });
  }
}
