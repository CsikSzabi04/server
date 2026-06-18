// recipes.ts — complete, ready-to-use project TEMPLATES the local brain can EMIT
// offline when asked to "build a website / page / app". The literal brain is a
// statistical engine, so it cannot invent novel code — but it CAN recall and hand
// back a full, working starter that the user can drop into a file and run. Each
// recipe is original, generic boilerplate with the official docs as the source.

export interface RecipeFile {
  name: string;
  code: string;
}
export interface WebRecipe {
  id: string;
  match: string[]; // trigger keywords (EN + HU)
  title: string;
  stack: string;
  summary: string;
  files: RecipeFile[];
  steps: string[];
  source: string;
}

export const WEB_RECIPES: WebRecipe[] = [
  // ── flagship: a complete responsive landing page in one file ─────────────────
  {
    id: 'landing',
    match: ['website', 'web', 'site', 'page', 'landing', 'homepage', 'home page', 'weboldal', 'oldal', 'honlap', 'kezdolap', 'weblap'],
    title: 'Responsive landing page',
    stack: 'HTML + CSS + a little JS',
    summary: 'A complete single-file landing page: sticky navbar, hero, feature cards, a call to action and a footer. Mobile-friendly with a flexible layout.',
    files: [
      {
        name: 'index.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>My Website</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; color: #1a1a2e; line-height: 1.6; }
    a { color: inherit; text-decoration: none; }
    .container { max-width: 1080px; margin: 0 auto; padding: 0 20px; }

    header { position: sticky; top: 0; background: #0f3460; color: #fff; }
    nav { display: flex; align-items: center; justify-content: space-between; height: 64px; }
    nav .logo { font-weight: 700; font-size: 1.2rem; }
    nav ul { display: flex; gap: 24px; list-style: none; }
    nav a:hover { opacity: .8; }

    .hero { background: linear-gradient(135deg, #0f3460, #16213e); color: #fff; text-align: center; padding: 96px 0; }
    .hero h1 { font-size: 2.6rem; margin-bottom: 16px; }
    .hero p { font-size: 1.15rem; opacity: .9; margin-bottom: 28px; }
    .btn { display: inline-block; background: #e94560; color: #fff; padding: 12px 28px; border-radius: 8px; font-weight: 600; }
    .btn:hover { background: #d63651; }

    .features { padding: 72px 0; }
    .features h2 { text-align: center; margin-bottom: 40px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; }
    .card { border: 1px solid #eee; border-radius: 12px; padding: 28px; box-shadow: 0 4px 16px rgba(0,0,0,.05); }
    .card h3 { margin-bottom: 8px; }

    footer { background: #16213e; color: #cbd5e1; text-align: center; padding: 32px 0; }

    @media (max-width: 640px) { nav ul { display: none; } .hero h1 { font-size: 2rem; } }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <nav>
        <div class="logo">My Website</div>
        <ul>
          <li><a href="#features">Features</a></li>
          <li><a href="#about">About</a></li>
          <li><a href="#contact">Contact</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <section class="hero">
    <div class="container">
      <h1>Build something people love</h1>
      <p>A clean, fast, responsive starting point for your idea.</p>
      <a class="btn" href="#features">Get started</a>
    </div>
  </section>

  <section class="features" id="features">
    <div class="container">
      <h2>What you get</h2>
      <div class="grid">
        <div class="card"><h3>Fast</h3><p>Loads instantly with no heavy framework.</p></div>
        <div class="card"><h3>Responsive</h3><p>Looks great on phone, tablet and desktop.</p></div>
        <div class="card"><h3>Simple</h3><p>One file you can edit and deploy in minutes.</p></div>
      </div>
    </div>
  </section>

  <footer><div class="container">© 2026 My Website. All rights reserved.</div></footer>
</body>
</html>`,
      },
    ],
    steps: [
      'Create a file called index.html and paste the code above.',
      'Double-click index.html to open it in your browser — it works with no build step.',
      'Edit the text, colours (the hex values) and links to make it yours.',
      'To publish, drop the file on any static host (GitHub Pages, Netlify, Vercel).',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web',
  },

  // ── React single-page starter ────────────────────────────────────────────────
  {
    id: 'react-app',
    match: ['react app', 'react site', 'react page', 'react weboldal', 'spa', 'react'],
    title: 'React starter app',
    stack: 'React + Vite',
    summary: 'A minimal React app with state, a list and an input — the core pieces of any interactive page.',
    files: [
      {
        name: 'src/App.jsx',
        code: `import { useState } from 'react';

export default function App() {
  const [text, setText] = useState('');
  const [items, setItems] = useState([]);

  function add() {
    if (!text.trim()) return;
    setItems([...items, { id: Date.now(), name: text }]);
    setText('');
  }

  return (
    <main style={{ maxWidth: 480, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>My React App</h1>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Add an item" />
        <button onClick={add}>Add</button>
      </div>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.name}</li>
        ))}
      </ul>
    </main>
  );
}`,
      },
    ],
    steps: [
      'Create the project: npm create vite@latest my-app -- --template react',
      'cd my-app, then npm install.',
      'Replace src/App.jsx with the code above.',
      'Run npm run dev and open the local URL it prints.',
    ],
    source: 'https://react.dev/learn',
  },

  // ── contact form page with basic validation ──────────────────────────────────
  {
    id: 'form',
    match: ['form', 'contact', 'contact form', 'kapcsolat', 'urlap', 'űrlap', 'signup', 'login form'],
    title: 'Contact form page',
    stack: 'HTML + CSS + JS',
    summary: 'A styled contact form with required fields and simple client-side validation.',
    files: [
      {
        name: 'contact.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Contact</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #f4f6fb; }
    form { max-width: 420px; margin: 60px auto; background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.08); }
    label { display: block; margin: 14px 0 6px; font-weight: 600; }
    input, textarea { width: 100%; padding: 10px; border: 1px solid #d0d5dd; border-radius: 8px; font: inherit; }
    button { margin-top: 18px; width: 100%; padding: 12px; border: 0; border-radius: 8px; background: #0f3460; color: #fff; font-weight: 600; cursor: pointer; }
    .ok { color: #0a7d32; margin-top: 12px; }
  </style>
</head>
<body>
  <form id="contact">
    <h2>Contact us</h2>
    <label for="name">Name</label>
    <input id="name" name="name" required />
    <label for="email">Email</label>
    <input id="email" name="email" type="email" required />
    <label for="message">Message</label>
    <textarea id="message" name="message" rows="4" required></textarea>
    <button type="submit">Send</button>
    <p class="ok" id="ok" hidden>Thanks! Your message was sent.</p>
  </form>
  <script>
    document.getElementById('contact').addEventListener('submit', (e) => {
      e.preventDefault();
      if (!e.target.checkValidity()) return;
      document.getElementById('ok').hidden = false;
      e.target.reset();
    });
  </script>
</body>
</html>`,
      },
    ],
    steps: [
      'Save the code as contact.html and open it in your browser.',
      'The browser enforces required and email validation automatically.',
      'To actually receive messages, post the form to a backend or a form service.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Learn/Forms',
  },

  // ── Node static file server ───────────────────────────────────────────────────
  {
    id: 'node-server',
    match: ['server', 'backend', 'node server', 'web server', 'api server', 'szerver', 'backend szerver'],
    title: 'Minimal Node web server',
    stack: 'Node.js',
    summary: 'A tiny HTTP server that serves an HTML page and a JSON API endpoint — no framework needed.',
    files: [
      {
        name: 'server.mjs',
        code: `import { createServer } from 'node:http';

const server = createServer((req, res) => {
  if (req.url === '/api/hello') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ message: 'Hello from Node' }));
    return;
  }
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end('<h1>Hello from Node</h1><p>Try <a href="/api/hello">/api/hello</a></p>');
});

server.listen(3000, () => console.log('Listening on http://localhost:3000'));`,
      },
    ],
    steps: [
      'Save the code as server.mjs.',
      'Run it with: node server.mjs',
      'Open http://localhost:3000 in your browser.',
    ],
    source: 'https://nodejs.org/docs/latest/api/http.html',
  },

  // ── Tailwind landing page ─────────────────────────────────────────────────────
  {
    id: 'tailwind-page',
    match: ['tailwind', 'tailwind page', 'tailwind site', 'tailwind weboldal'],
    title: 'Tailwind CSS landing page',
    stack: 'HTML + Tailwind (CDN)',
    summary: 'A landing page built with Tailwind utility classes, using the CDN so there is no build step.',
    files: [
      {
        name: 'index.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tailwind Site</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="text-slate-800">
  <header class="bg-slate-900 text-white">
    <nav class="max-w-5xl mx-auto flex items-center justify-between h-16 px-4">
      <span class="font-bold">Tailwind Site</span>
      <a href="#" class="hover:opacity-80">Contact</a>
    </nav>
  </header>
  <section class="bg-gradient-to-br from-slate-900 to-slate-700 text-white text-center py-24 px-4">
    <h1 class="text-4xl font-bold mb-4">Ship faster with utility classes</h1>
    <p class="opacity-90 mb-8">Style directly in your markup, no custom CSS file.</p>
    <a href="#" class="inline-block bg-rose-500 hover:bg-rose-600 px-6 py-3 rounded-lg font-semibold">Get started</a>
  </section>
  <section class="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 py-16 px-4">
    <div class="rounded-xl border p-6 shadow-sm"><h3 class="font-semibold mb-2">Fast</h3><p>No build step with the CDN.</p></div>
    <div class="rounded-xl border p-6 shadow-sm"><h3 class="font-semibold mb-2">Responsive</h3><p>md and lg prefixes adapt the layout.</p></div>
    <div class="rounded-xl border p-6 shadow-sm"><h3 class="font-semibold mb-2">Consistent</h3><p>Shared spacing and colour scales.</p></div>
  </section>
</body>
</html>`,
      },
    ],
    steps: [
      'Save the code as index.html and open it in your browser.',
      'The Tailwind CDN script makes every utility class available immediately.',
      'For production, install Tailwind with a build step so unused classes are removed.',
    ],
    source: 'https://tailwindcss.com/docs/installation/play-cdn',
  },

  // ── blog / articles page ──────────────────────────────────────────────────────
  {
    id: 'blog',
    match: ['blog', 'articles', 'article page', 'news', 'posts', 'blog page', 'hir', 'cikk', 'blogot'],
    title: 'Blog / articles page',
    stack: 'HTML + CSS',
    summary: 'A clean blog layout: a header, a list of article cards with title, date and excerpt, and a sidebar.',
    files: [
      {
        name: 'blog.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>My Blog</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Georgia, serif; margin: 0; color: #222; background: #fafafa; }
    header { background: #1f2937; color: #fff; padding: 28px 20px; text-align: center; }
    .wrap { max-width: 900px; margin: 0 auto; padding: 24px 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 28px; }
    article { background: #fff; border-radius: 10px; padding: 22px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
    article h2 { margin: 0 0 6px; }
    .date { color: #888; font-size: .85rem; }
    aside { background: #fff; border-radius: 10px; padding: 22px; height: fit-content; }
    a { color: #2563eb; }
    @media (max-width: 720px) { .wrap { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header><h1>My Blog</h1><p>Thoughts on code and design</p></header>
  <div class="wrap">
    <main>
      <article>
        <h2><a href="#">First post</a></h2>
        <p class="date">June 16, 2026</p>
        <p>This is the excerpt of the first article. Click the title to read more.</p>
      </article>
      <article>
        <h2><a href="#">Second post</a></h2>
        <p class="date">June 10, 2026</p>
        <p>A short summary of the second article goes right here.</p>
      </article>
    </main>
    <aside>
      <h3>About</h3>
      <p>A small blog built with plain HTML and CSS.</p>
      <h3>Links</h3>
      <ul><li><a href="#">Archive</a></li><li><a href="#">Contact</a></li></ul>
    </aside>
  </div>
</body>
</html>`,
      },
    ],
    steps: [
      'Save the code as blog.html and open it in your browser.',
      'Duplicate an <article> block for each new post.',
      'Later, generate the article list from data or a Markdown folder.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Document_and_website_structure',
  },

  // ── responsive image gallery ────────────────────────────────────────────────
  {
    id: 'gallery',
    match: ['gallery', 'image grid', 'photos', 'portfolio', 'galeria', 'kepek', 'galériát'],
    title: 'Responsive image gallery',
    stack: 'HTML + CSS Grid',
    summary: 'A responsive photo grid that reflows from one column on phones to many on desktop.',
    files: [
      {
        name: 'gallery.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gallery</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #0b1020; color: #fff; }
    h1 { text-align: center; padding: 24px; }
    .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; padding: 0 16px 32px; }
    .gallery figure { margin: 0; overflow: hidden; border-radius: 10px; }
    .gallery img { width: 100%; height: 180px; object-fit: cover; display: block; transition: transform .3s; }
    .gallery img:hover { transform: scale(1.06); }
  </style>
</head>
<body>
  <h1>My Gallery</h1>
  <div class="gallery">
    <figure><img src="https://picsum.photos/seed/1/400/300" alt="" /></figure>
    <figure><img src="https://picsum.photos/seed/2/400/300" alt="" /></figure>
    <figure><img src="https://picsum.photos/seed/3/400/300" alt="" /></figure>
    <figure><img src="https://picsum.photos/seed/4/400/300" alt="" /></figure>
    <figure><img src="https://picsum.photos/seed/5/400/300" alt="" /></figure>
    <figure><img src="https://picsum.photos/seed/6/400/300" alt="" /></figure>
  </div>
</body>
</html>`,
      },
    ],
    steps: [
      'Save as gallery.html and open it in your browser.',
      'Replace the image URLs with your own photos.',
      'The grid adapts automatically — no media queries needed thanks to auto-fill.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout',
  },

  // ── pricing page ──────────────────────────────────────────────────────────────
  {
    id: 'pricing',
    match: ['pricing', 'plans', 'pricing page', 'subscription', 'arazas', 'csomagok', 'árazás'],
    title: 'Pricing page',
    stack: 'HTML + CSS',
    summary: 'Three pricing cards side by side, with the middle plan highlighted as the popular choice.',
    files: [
      {
        name: 'pricing.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pricing</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #f3f4f6; margin: 0; }
    h1 { text-align: center; padding: 40px 0 8px; }
    .plans { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; padding: 24px; }
    .plan { background: #fff; border-radius: 14px; padding: 28px; width: 260px; box-shadow: 0 6px 20px rgba(0,0,0,.07); text-align: center; }
    .plan.popular { border: 2px solid #6366f1; transform: scale(1.04); }
    .price { font-size: 2.4rem; font-weight: 800; margin: 12px 0; }
    .plan ul { list-style: none; padding: 0; color: #555; }
    .plan li { padding: 6px 0; border-bottom: 1px solid #eee; }
    .plan button { margin-top: 16px; width: 100%; padding: 12px; border: 0; border-radius: 8px; background: #6366f1; color: #fff; font-weight: 600; cursor: pointer; }
  </style>
</head>
<body>
  <h1>Choose your plan</h1>
  <div class="plans">
    <div class="plan"><h3>Starter</h3><div class="price">$0</div><ul><li>1 project</li><li>Community support</li></ul><button>Choose</button></div>
    <div class="plan popular"><h3>Pro</h3><div class="price">$9</div><ul><li>Unlimited projects</li><li>Priority support</li></ul><button>Choose</button></div>
    <div class="plan"><h3>Team</h3><div class="price">$29</div><ul><li>Everything in Pro</li><li>5 seats</li></ul><button>Choose</button></div>
  </div>
</body>
</html>`,
      },
    ],
    steps: [
      'Save as pricing.html and open it in your browser.',
      'Edit the plan names, prices and feature lists.',
      'Wire each button to your checkout or signup flow.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout',
  },

  // ── admin dashboard layout ────────────────────────────────────────────────────
  {
    id: 'dashboard',
    match: ['dashboard', 'admin', 'admin panel', 'sidebar layout', 'panel', 'iranyitopult'],
    title: 'Dashboard layout',
    stack: 'HTML + CSS Grid',
    summary: 'An app shell with a fixed sidebar, a top bar and a main area of stat cards.',
    files: [
      {
        name: 'dashboard.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, sans-serif; display: grid; grid-template-columns: 220px 1fr; grid-template-rows: 56px 1fr; min-height: 100vh; }
    .sidebar { grid-row: 1 / 3; background: #111827; color: #cbd5e1; padding: 20px; }
    .sidebar a { display: block; color: #cbd5e1; text-decoration: none; padding: 10px; border-radius: 8px; }
    .sidebar a:hover { background: #1f2937; color: #fff; }
    .topbar { background: #fff; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; padding: 0 20px; font-weight: 600; }
    main { background: #f9fafb; padding: 20px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
    .stat { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,.05); }
    .stat .n { font-size: 2rem; font-weight: 800; }
  </style>
</head>
<body>
  <nav class="sidebar"><h2>Admin</h2><a href="#">Overview</a><a href="#">Users</a><a href="#">Settings</a></nav>
  <header class="topbar">Dashboard</header>
  <main>
    <div class="cards">
      <div class="stat"><div class="n">1,204</div><div>Users</div></div>
      <div class="stat"><div class="n">$8.3k</div><div>Revenue</div></div>
      <div class="stat"><div class="n">96%</div><div>Uptime</div></div>
    </div>
  </main>
</body>
</html>`,
      },
    ],
    steps: [
      'Save as dashboard.html and open it in your browser.',
      'Add links to the sidebar and more cards to the grid.',
      'Fill the numbers from real data with a small fetch call.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout',
  },

  // ── interactive vanilla-JS todo app ────────────────────────────────────────────
  {
    id: 'todo',
    match: ['todo', 'to do', 'todo app', 'task app', 'task list', 'teendo', 'feladatlista', 'todot'],
    title: 'Interactive to-do app',
    stack: 'HTML + CSS + JS',
    summary: 'A working to-do app in one file: add items, mark them done, delete them, saved in localStorage.',
    files: [
      {
        name: 'todo.html',
        code: `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>To-do</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 420px; margin: 40px auto; }
    .row { display: flex; gap: 8px; }
    input { flex: 1; padding: 10px; }
    button { padding: 10px 14px; cursor: pointer; }
    ul { list-style: none; padding: 0; }
    li { display: flex; align-items: center; gap: 8px; padding: 8px; border-bottom: 1px solid #eee; }
    li.done span { text-decoration: line-through; color: #999; }
    li span { flex: 1; }
  </style>
</head>
<body>
  <h1>To-do</h1>
  <div class="row"><input id="text" placeholder="What needs doing?" /><button id="add">Add</button></div>
  <ul id="list"></ul>
  <script>
    const list = document.getElementById('list');
    let items = JSON.parse(localStorage.getItem('todo') || '[]');
    function save() { localStorage.setItem('todo', JSON.stringify(items)); }
    function render() {
      list.innerHTML = '';
      items.forEach((it, i) => {
        const li = document.createElement('li');
        if (it.done) li.className = 'done';
        li.innerHTML = '<input type="checkbox" ' + (it.done ? 'checked' : '') + '/><span>' + it.text + '</span><button>x</button>';
        li.querySelector('input').onchange = () => { items[i].done = !items[i].done; save(); render(); };
        li.querySelector('button').onclick = () => { items.splice(i, 1); save(); render(); };
        list.appendChild(li);
      });
    }
    document.getElementById('add').onclick = () => {
      const t = document.getElementById('text');
      if (!t.value.trim()) return;
      items.push({ text: t.value, done: false }); t.value = ''; save(); render();
    };
    render();
  </script>
</body>
</html>`,
      },
    ],
    steps: [
      'Save as todo.html and open it in your browser.',
      'Type a task and press Add; tick the box to complete, x to delete.',
      'Your list is saved in the browser via localStorage and survives a refresh.',
    ],
    source: 'https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage',
  },
];

// Descriptive sentences (fed to the learner for vocabulary + a "how to build a
// website" conceptual answer; the actual code lives in the recipes above).
export const RECIPE_TEXT: string[] = [
  'To build a website you usually start with an HTML file that holds the structure, add CSS for the style, and a little JavaScript for behaviour.',
  'A simple website has a header with a navigation bar, a hero section with a title and a button, a few content sections, and a footer at the bottom.',
  'Make a layout responsive with a flexible container, a grid that wraps, and media queries so it looks good on phone, tablet and desktop.',
  'A single HTML file with inline CSS needs no build step: save it, open it in the browser, then host it on a static service like GitHub Pages, Netlify or Vercel.',
  'For an interactive app, React splits the page into components, keeps data in state, and updates the screen when the state changes.',
  'A contact form uses input and textarea fields with the required attribute, and the browser validates them before the form is sent.',
  'A backend server in Node listens on a port, answers requests, and can return HTML pages or JSON data from an API endpoint.',
  'A blog page lists articles as cards with a title, a date and a short excerpt, often with a sidebar for links and an about box.',
  'An image gallery uses a CSS grid with auto-fill so the photos reflow from one column on a phone to many columns on a wide screen.',
  'A pricing page shows a few plan cards side by side, usually with the middle plan highlighted as the most popular choice.',
  'A dashboard has a fixed sidebar for navigation, a top bar, and a main area of stat cards laid out in a responsive grid.',
  'A to-do app adds items to a list, marks them done with a checkbox, deletes them, and saves the list in localStorage so it survives a refresh.',
];

// Build-intent verbs (EN + HU). Loose substring match so Hungarian suffixes
// (csinálj, készíts, szeretnék, weboldalt) and English forms all trigger.
const BUILD_INTENT = /(build|make|create|generate|write|code\s|csin[aá]l|k[eé]sz[ií]t|[eé]p[ií]t|gener[aá]l|[ií]r[jd]|szeretn|akar|kell|k[eé]rek|k[eé]rlek|want|need)/;

/** Detect a "build me a website / page / app" request and pick the best template. */
export function findRecipe(query: string): WebRecipe | null {
  const q = query.toLowerCase();
  const wantsBuild = BUILD_INTENT.test(q);
  let best: WebRecipe | null = null;
  let bestScore = 0;
  for (const r of WEB_RECIPES) {
    let score = 0;
    for (const m of r.match) if (q.includes(m)) score += m.includes(' ') ? 3 : 2;
    // A specific template beats the generic landing page on a tie (e.g. "pricing page").
    const beatsTie = score === bestScore && best?.id === 'landing' && r.id !== 'landing';
    if (score > bestScore || beatsTie) {
      bestScore = score;
      best = r;
    }
  }
  // Fire when the user asks to build something (any matched template), OR when they
  // strongly name a specific template (e.g. "react app", "contact form").
  if (best && (wantsBuild || bestScore >= 4)) return best;
  return null;
}

/** Render a recipe as a single text answer (summary + files + steps + source). */
export function renderRecipe(r: WebRecipe): string {
  const files = r.files
    .map((f) => `// ${f.name}\n${f.code}`)
    .join('\n\n');
  const steps = r.steps.map((s, i) => `${i + 1}. ${s}`).join('\n');
  return `${r.title} (${r.stack})\n${r.summary}\n\n${files}\n\nSteps:\n${steps}\n\nSource: ${r.source}`;
}
