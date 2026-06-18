// ingest-programming.mjs — OFFLINE build-time ingest for the BRAIN's Programming
// region. Owned by AI-3 (BODY / build tooling). Runs in Node at build time — NOT in
// the browser brain (the runtime brain has no network/keys). It emits a SEPARATE
// static file (src/brain/seed/programming.ingested.ts) that AI-1's seedProgramming
// consumes (it uses these chunks when non-empty). It NEVER writes programming.gen.ts.
//
// The corpus below is a large, curated, WEBSITE-BUILDING-focused knowledge base:
// concepts (→ vocab/Markov phrasing) + complete, copy-paste code snippets (stored
// verbatim as `doc` nodes the brain can retrieve and cite with their source URL).
// Best-effort live fetch of the official docs is appended when online; fully offline
// it still emits the whole curated corpus, so the build NEVER depends on the network.
// No external npm packages (Node 18+ global fetch + regex HTML cleaning).
//
// Usage:
//   npm run ingest:brain                 # curated corpus + best-effort live docs
//   npm run ingest:brain -- --offline    # curated corpus only (deterministic)
//   node scripts/ingest-programming.mjs --out <path>
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SEED_VERSION = 4;

// ── Curated source / link registry (official docs per technology) ─────────────
const SOURCES = [
  { tech: 'html', title: 'MDN — HTML', url: 'https://developer.mozilla.org/en-US/docs/Web/HTML', topics: ['elements', 'forms', 'semantics', 'attributes', 'website'] },
  { tech: 'css', title: 'MDN — CSS', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS', topics: ['flexbox', 'grid', 'selectors', 'box-model', 'responsive', 'layout'] },
  { tech: 'javascript', title: 'MDN — JavaScript', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript', topics: ['functions', 'promises', 'closures', 'arrays', 'dom', 'fetch', 'events'] },
  { tech: 'react', title: 'React docs', url: 'https://react.dev/learn', topics: ['components', 'hooks', 'usestate', 'useeffect', 'jsx', 'props', 'state'] },
  { tech: 'node', title: 'Node.js API docs', url: 'https://nodejs.org/docs/latest/api/', topics: ['fs', 'http', 'modules', 'express', 'server', 'api'] },
  { tech: 'tailwind', title: 'Tailwind CSS docs', url: 'https://tailwindcss.com/docs', topics: ['utility', 'responsive', 'flex', 'grid', 'spacing', 'website'] },
  { tech: 'bootstrap', title: 'Bootstrap docs', url: 'https://getbootstrap.com/docs/', topics: ['grid', 'components', 'utilities', 'breakpoints', 'navbar'] },
  { tech: 'java', title: 'Java SE documentation', url: 'https://docs.oracle.com/en/java/javase/', topics: ['classes', 'jvm', 'collections', 'generics', 'spring'] },
  { tech: 'native', title: 'React Native docs', url: 'https://reactnative.dev/docs/getting-started', topics: ['components', 'navigation', 'platform', 'mobile'] },
  { tech: 'native', title: 'Android developers', url: 'https://developer.android.com/', topics: ['android', 'activity', 'kotlin'] },
  { tech: 'native', title: 'Apple developer docs', url: 'https://developer.apple.com/documentation/', topics: ['ios', 'swiftui', 'uikit'] },
  { tech: 'website', title: 'MDN — Getting started building a website', url: 'https://developer.mozilla.org/en-US/docs/Learn', topics: ['website', 'frontend', 'deploy', 'seo', 'fullstack'] },
  { tech: 'database', title: 'Prisma docs', url: 'https://www.prisma.io/docs', topics: ['sql', 'orm', 'postgres', 'mongodb', 'query', 'database'] },
  { tech: 'auth', title: 'Supabase Auth docs', url: 'https://supabase.com/docs/guides/auth', topics: ['jwt', 'oauth', 'session', 'login', 'security', 'auth'] },
  { tech: 'testing', title: 'Vitest docs', url: 'https://vitest.dev/guide/', topics: ['unit', 'e2e', 'jest', 'playwright', 'ci', 'testing'] },
  { tech: 'animation', title: 'MDN — CSS animations', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations', topics: ['transition', 'keyframes', 'raf', 'motion', 'animation'] },
  { tech: 'python', title: 'Python docs', url: 'https://docs.python.org/3/', topics: ['python', 'syntax', 'stdlib', 'flask', 'django'] },
  { tech: 'kotlin', title: 'Kotlin docs', url: 'https://kotlinlang.org/docs/home.html', topics: ['kotlin', 'android', 'jvm', 'coroutines'] },
  { tech: 'php', title: 'PHP manual', url: 'https://www.php.net/manual/en/', topics: ['php', 'web', 'mysql', 'laravel'] },
  { tech: 'mysql', title: 'MySQL docs', url: 'https://dev.mysql.com/doc/', topics: ['mysql', 'sql', 'database', 'query', 'phpmyadmin'] },
  { tech: 'vite', title: 'Vite guide', url: 'https://vitejs.dev/guide/', topics: ['vite', 'build', 'bundler', 'dev', 'hmr'] },
  { tech: 'oracle', title: 'Oracle Java & DB docs', url: 'https://docs.oracle.com/en/', topics: ['oracle', 'java', 'database', 'plsql'] },
];

// Many official doc pages pulled live (best-effort, parallel) for breadth/volume —
// this is what makes the brain "draw itself". Skipped under --offline.
const FETCH_URLS = [
  { tech: 'html', url: 'https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Getting_started' },
  { tech: 'html', url: 'https://developer.mozilla.org/en-US/docs/Learn/Forms/Your_first_form' },
  { tech: 'html', url: 'https://developer.mozilla.org/en-US/docs/Glossary/Semantics' },
  { tech: 'css', url: 'https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Flexbox' },
  { tech: 'css', url: 'https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Grids' },
  { tech: 'css', url: 'https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/The_box_model' },
  { tech: 'css', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries/Using_media_queries' },
  { tech: 'javascript', url: 'https://developer.mozilla.org/en-US/docs/Learn/JavaScript/First_steps/What_is_JavaScript' },
  { tech: 'javascript', url: 'https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch' },
  { tech: 'javascript', url: 'https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Client-side_web_APIs/Manipulating_documents' },
  { tech: 'javascript', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Functions' },
  { tech: 'javascript', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises' },
  { tech: 'react', url: 'https://react.dev/learn' },
  { tech: 'react', url: 'https://react.dev/learn/describing-the-ui' },
  { tech: 'react', url: 'https://react.dev/learn/adding-interactivity' },
  { tech: 'react', url: 'https://react.dev/learn/managing-state' },
  { tech: 'react', url: 'https://react.dev/reference/react/useState' },
  { tech: 'react', url: 'https://react.dev/reference/react/useEffect' },
  { tech: 'node', url: 'https://nodejs.org/en/learn/getting-started/introduction-to-nodejs' },
  { tech: 'node', url: 'https://expressjs.com/en/starter/hello-world.html' },
  { tech: 'node', url: 'https://expressjs.com/en/guide/routing.html' },
  { tech: 'node', url: 'https://expressjs.com/en/starter/static-files.html' },
  { tech: 'tailwind', url: 'https://tailwindcss.com/docs/utility-first' },
  { tech: 'tailwind', url: 'https://tailwindcss.com/docs/flex' },
  { tech: 'tailwind', url: 'https://tailwindcss.com/docs/grid-template-columns' },
  { tech: 'tailwind', url: 'https://tailwindcss.com/docs/responsive-design' },
  { tech: 'bootstrap', url: 'https://getbootstrap.com/docs/5.3/getting-started/introduction/' },
  { tech: 'bootstrap', url: 'https://getbootstrap.com/docs/5.3/layout/grid/' },
  { tech: 'bootstrap', url: 'https://getbootstrap.com/docs/5.3/components/buttons/' },
  { tech: 'typescript', url: 'https://www.typescriptlang.org/docs/handbook/2/everyday-types.html' },
  { tech: 'typescript', url: 'https://www.typescriptlang.org/docs/handbook/2/functions.html' },
  { tech: 'typescript', url: 'https://www.typescriptlang.org/docs/handbook/2/objects.html' },
  { tech: 'git', url: 'https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F' },
  { tech: 'git', url: 'https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository' },
  { tech: 'java', url: 'https://docs.oracle.com/javase/tutorial/java/concepts/index.html' },
  { tech: 'native', url: 'https://reactnative.dev/docs/getting-started' },
  { tech: 'native', url: 'https://reactnative.dev/docs/intro-react' },
  { tech: 'website', url: 'https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web' },
  { tech: 'website', url: 'https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Tools_and_setup/How_do_you_host_your_website_on_GitHub_Pages' },
  { tech: 'website', url: 'https://developer.mozilla.org/en-US/docs/Web/Accessibility' },
  { tech: 'database', url: 'https://www.prisma.io/docs/getting-started' },
  { tech: 'database', url: 'https://www.postgresql.org/docs/current/tutorial-sql.html' },
  { tech: 'database', url: 'https://www.mongodb.com/docs/manual/introduction/' },
  { tech: 'auth', url: 'https://supabase.com/docs/guides/auth' },
  { tech: 'auth', url: 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication' },
  { tech: 'auth', url: 'https://jwt.io/introduction' },
  { tech: 'testing', url: 'https://vitest.dev/guide/' },
  { tech: 'testing', url: 'https://jestjs.io/docs/getting-started' },
  { tech: 'testing', url: 'https://playwright.dev/docs/intro' },
  { tech: 'animation', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations/Using_CSS_animations' },
  { tech: 'animation', url: 'https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame' },
  { tech: 'animation', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_transitions/Using_CSS_transitions' },
  { tech: 'git', url: 'https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging' },
  { tech: 'git', url: 'https://git-scm.com/book/en/v2/Git-Branching-Rebasing' },
  { tech: 'python', url: 'https://docs.python.org/3/tutorial/introduction.html' },
  { tech: 'python', url: 'https://docs.python.org/3/tutorial/controlflow.html' },
  { tech: 'python', url: 'https://docs.python.org/3/tutorial/datastructures.html' },
  { tech: 'kotlin', url: 'https://kotlinlang.org/docs/basic-syntax.html' },
  { tech: 'kotlin', url: 'https://kotlinlang.org/docs/classes.html' },
  { tech: 'php', url: 'https://www.php.net/manual/en/language.basic-syntax.php' },
  { tech: 'php', url: 'https://www.php.net/manual/en/language.types.php' },
  { tech: 'php', url: 'https://www.php.net/manual/en/mysqli.quickstart.php' },
  { tech: 'mysql', url: 'https://dev.mysql.com/doc/refman/8.0/en/tutorial.html' },
  { tech: 'mysql', url: 'https://dev.mysql.com/doc/refman/8.0/en/select.html' },
  { tech: 'vite', url: 'https://vitejs.dev/guide/' },
  { tech: 'vite', url: 'https://vitejs.dev/guide/features.html' },
  { tech: 'phpmyadmin', url: 'https://docs.phpmyadmin.net/en/latest/' },
];

// ── Curated knowledge base: concepts (prose) + snippets (verbatim code) ────────
const CORPUS = {
  html: {
    concepts: [
      `HTML, HyperText Markup Language, structures the content of a web page using elements written as tags. A document starts with the doctype, then html, head and body. The head holds metadata like the title, character set and viewport; the body holds the visible content. Semantic elements describe meaning: header, nav, main, section, article, aside and footer. Use headings h1 to h6 for structure, p for paragraphs, a for links, img for images, ul and ol for lists.`,
      `Forms collect user input. The form element wraps inputs and has an action and method. Common controls are input with types like text, email, password, number, checkbox and radio, plus textarea, select and button. Always pair each input with a label for accessibility, and use the name attribute so the value is submitted. Buttons of type submit send the form; type button does nothing by default.`,
      `Accessibility and SEO start in the HTML: use semantic tags, alt text on images, a single descriptive h1, meta description, and a responsive viewport meta tag. Link CSS in the head with a link tag and load JavaScript with a script tag, preferably with the defer attribute so it runs after the HTML is parsed.`,
    ],
    snippets: [
      { title: 'Complete HTML5 page skeleton', code: `<!doctype html>\n<html lang="en">\n  <head>\n    <meta charset="utf-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <meta name="description" content="A starter website" />\n    <title>My Website</title>\n    <link rel="stylesheet" href="style.css" />\n  </head>\n  <body>\n    <header><h1>My Website</h1></header>\n    <main>\n      <section><p>Welcome to my site.</p></section>\n    </main>\n    <footer><p>&copy; 2026</p></footer>\n    <script src="app.js" defer></script>\n  </body>\n</html>` },
      { title: 'Semantic page layout (header, nav, main, footer)', code: `<header>\n  <nav>\n    <a href="/">Home</a>\n    <a href="/about">About</a>\n    <a href="/contact">Contact</a>\n  </nav>\n</header>\n<main>\n  <article>\n    <h2>Article title</h2>\n    <p>Article body...</p>\n  </article>\n  <aside>Related links</aside>\n</main>\n<footer>Contact: hello@example.com</footer>` },
      { title: 'Accessible contact form', code: `<form action="/contact" method="post">\n  <label for="name">Name</label>\n  <input id="name" name="name" type="text" required />\n  <label for="email">Email</label>\n  <input id="email" name="email" type="email" required />\n  <label for="msg">Message</label>\n  <textarea id="msg" name="message" rows="4"></textarea>\n  <button type="submit">Send</button>\n</form>` },
    ],
  },
  css: {
    concepts: [
      `CSS, Cascading Style Sheets, controls how HTML looks: colors, fonts, spacing and layout. Rules have a selector and a declaration block of property and value pairs. Selectors target elements by tag, class with a dot, or id with a hash. The box model is content, padding, border and margin; box-sizing border-box makes width include padding and border, which is easier to reason about.`,
      `Flexbox lays out items in one dimension. Set display flex on a container; justify-content aligns along the main axis, align-items along the cross axis, and gap adds spacing. Grid lays out in two dimensions with display grid, grid-template-columns and gap; use repeat and minmax with auto-fit for responsive card grids. Position can be static, relative, absolute, fixed or sticky.`,
      `Responsive design adapts to screen size with media queries and relative units like rem, percentages, vw and vh. Mobile-first means writing base styles for small screens and adding min-width media queries for larger ones. CSS custom properties, written with two dashes, hold reusable values like theme colors and are read with the var function.`,
    ],
    snippets: [
      { title: 'Center anything with flexbox', code: `.center {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  min-height: 100vh;\n}` },
      { title: 'Responsive auto-fit card grid', code: `.grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));\n  gap: 16px;\n}` },
      { title: 'Theme with CSS variables + reset', code: `:root {\n  --bg: #0b0f17;\n  --text: #e6f0ff;\n  --accent: #1fe5ff;\n}\n* { box-sizing: border-box; margin: 0; }\nbody {\n  background: var(--bg);\n  color: var(--text);\n  font-family: system-ui, sans-serif;\n  line-height: 1.5;\n}` },
      { title: 'Sticky responsive navbar', code: `.nav {\n  position: sticky;\n  top: 0;\n  display: flex;\n  gap: 16px;\n  padding: 12px 20px;\n  background: #111;\n}\n@media (max-width: 600px) {\n  .nav { flex-direction: column; }\n}` },
    ],
  },
  javascript: {
    concepts: [
      `JavaScript makes web pages interactive. It runs in the browser and on servers with Node. Declare variables with const for values that do not change and let otherwise. Core types are string, number, boolean, null, undefined, object and array. Functions are first-class; arrow functions are short syntax. Arrays have map, filter, reduce and forEach; objects hold key-value pairs.`,
      `The DOM is the page as a tree of nodes. Select elements with document.querySelector and querySelectorAll, read or set textContent and value, and change classes with classList. Listen for user actions with addEventListener, passing an event type like click, input or submit and a handler function. Call event.preventDefault to stop a form from reloading the page.`,
      `Asynchronous code handles things that take time, like network requests. The fetch function returns a promise; await it inside an async function, check response.ok, then await response.json. Use try and catch for errors. Store small data in localStorage with setItem and getItem; it persists in the browser.`,
    ],
    snippets: [
      { title: 'Select an element and handle a click', code: `const btn = document.querySelector('#save');\nlet count = 0;\nbtn.addEventListener('click', () => {\n  count += 1;\n  btn.textContent = 'Clicked ' + count;\n});` },
      { title: 'Fetch JSON and render a list', code: `async function loadUsers() {\n  const res = await fetch('/api/users');\n  if (!res.ok) throw new Error('HTTP ' + res.status);\n  const users = await res.json();\n  const ul = document.querySelector('#list');\n  ul.innerHTML = users.map((u) => '<li>' + u.name + '</li>').join('');\n}\nloadUsers().catch((e) => console.error(e));` },
      { title: 'Submit a form with fetch POST', code: `const form = document.querySelector('#contact');\nform.addEventListener('submit', async (e) => {\n  e.preventDefault();\n  const data = Object.fromEntries(new FormData(form));\n  const res = await fetch('/api/contact', {\n    method: 'POST',\n    headers: { 'content-type': 'application/json' },\n    body: JSON.stringify(data),\n  });\n  alert(res.ok ? 'Sent!' : 'Failed');\n});` },
    ],
  },
  react: {
    concepts: [
      `React builds user interfaces from reusable components. A component is a function that returns JSX, an HTML-like syntax. Components receive inputs called props and re-render when their props or state change. Render lists by mapping an array to elements and giving each a unique key. Conditionally render with the ternary operator or logical and.`,
      `Hooks add state and behavior to function components. useState returns the current value and a setter; calling the setter re-renders. useEffect runs side effects like data fetching after render, controlled by a dependency array; return a cleanup function when needed. Keep components small and lift shared state up to a common parent.`,
      `A typical React app is built with Vite. The index.html has a div with id root and loads src/main.jsx, which creates a root and renders the App component. Event handlers are passed as props like onClick and onChange. Controlled inputs read value from state and update it in onChange.`,
    ],
    snippets: [
      { title: 'Counter component with useState', code: `import { useState } from 'react';\n\nexport default function Counter() {\n  const [n, setN] = useState(0);\n  return (\n    <button onClick={() => setN(n + 1)}>\n      Clicked {n} times\n    </button>\n  );\n}` },
      { title: 'Fetch data with useEffect and render a list', code: `import { useEffect, useState } from 'react';\n\nexport default function Users() {\n  const [users, setUsers] = useState([]);\n  useEffect(() => {\n    fetch('/api/users')\n      .then((r) => r.json())\n      .then(setUsers);\n  }, []);\n  return (\n    <ul>\n      {users.map((u) => (\n        <li key={u.id}>{u.name}</li>\n      ))}\n    </ul>\n  );\n}` },
      { title: 'Controlled form component', code: `import { useState } from 'react';\n\nexport default function ContactForm() {\n  const [email, setEmail] = useState('');\n  const submit = (e) => {\n    e.preventDefault();\n    fetch('/api/contact', { method: 'POST', body: email });\n  };\n  return (\n    <form onSubmit={submit}>\n      <input value={email} onChange={(e) => setEmail(e.target.value)} />\n      <button>Send</button>\n    </form>\n  );\n}` },
      { title: 'Vite entry: index.html + src/main.jsx', code: `<!-- index.html -->\n<div id="root"></div>\n<script type="module" src="/src/main.jsx"></script>\n\n// src/main.jsx\nimport { createRoot } from 'react-dom/client';\nimport App from './App.jsx';\ncreateRoot(document.getElementById('root')).render(<App />);` },
    ],
  },
  node: {
    concepts: [
      `Node.js runs JavaScript on the server using the V8 engine with an event-driven, non-blocking model. It is ideal for web servers and APIs. Code is organized into modules; ES modules use import and export, CommonJS uses require and module.exports. A package.json describes the project, its scripts and dependencies, installed with npm install.`,
      `Express is the most common Node web framework. You create an app, define routes for HTTP methods like get and post, and start listening on a port. Middleware runs on every request, for example express.json to parse JSON bodies and express.static to serve a folder of files. Routes send responses with res.send, res.json or res.sendFile.`,
    ],
    snippets: [
      { title: 'Express server: static site + JSON API', code: `import express from 'express';\nconst app = express();\napp.use(express.json());\napp.use(express.static('public'));\n\napp.get('/api/users', (req, res) => {\n  res.json([{ id: 1, name: 'Ada' }]);\n});\n\napp.post('/api/contact', (req, res) => {\n  console.log('message:', req.body);\n  res.json({ ok: true });\n});\n\napp.listen(3000, () => console.log('http://localhost:3000'));` },
      { title: 'Minimal Node HTTP server (no deps)', code: `import http from 'node:http';\nhttp\n  .createServer((req, res) => {\n    res.writeHead(200, { 'content-type': 'text/html' });\n    res.end('<h1>Hello from Node</h1>');\n  })\n  .listen(3000);` },
      { title: 'package.json for a web app', code: `{\n  "name": "my-site",\n  "type": "module",\n  "scripts": {\n    "dev": "vite",\n    "build": "vite build",\n    "start": "node server.js"\n  }\n}` },
    ],
  },
  tailwind: {
    concepts: [
      `Tailwind CSS is a utility-first framework: instead of writing CSS, you compose small classes in the HTML. Spacing uses p and m with a scale like p-4 and mx-auto; layout uses flex, grid, items-center and justify-between; colors use bg- and text- with a shade like bg-blue-600 and text-white; typography uses text-xl and font-bold. Responsive prefixes like sm, md and lg apply at breakpoints, for example md:flex.`,
    ],
    snippets: [
      { title: 'Tailwind hero section', code: `<section class="min-h-screen flex flex-col items-center justify-center bg-gray-900 text-white">\n  <h1 class="text-4xl font-bold mb-4">Build something great</h1>\n  <p class="text-gray-300 mb-6">A starter landing page.</p>\n  <a href="#" class="px-6 py-3 rounded-lg bg-cyan-500 text-black font-semibold">Get started</a>\n</section>` },
      { title: 'Tailwind responsive card grid', code: `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 p-6">\n  <div class="rounded-xl bg-white shadow p-5">\n    <h3 class="font-bold text-lg">Card</h3>\n    <p class="text-gray-600">Description</p>\n  </div>\n</div>` },
    ],
  },
  bootstrap: {
    concepts: [
      `Bootstrap is a CSS and component framework with a responsive twelve-column grid. Wrap content in a container, then rows of columns using col classes; columns automatically share the width. It ships ready components like navbar, buttons, cards, modals and forms, and utility classes for spacing and colors. Breakpoints sm, md, lg and xl control responsive behavior.`,
    ],
    snippets: [
      { title: 'Bootstrap responsive grid + card', code: `<div class="container py-4">\n  <div class="row g-3">\n    <div class="col-12 col-md-6 col-lg-4">\n      <div class="card">\n        <div class="card-body">\n          <h5 class="card-title">Title</h5>\n          <p class="card-text">Some text.</p>\n          <a href="#" class="btn btn-primary">Go</a>\n        </div>\n      </div>\n    </div>\n  </div>\n</div>` },
    ],
  },
  java: {
    concepts: [
      `Java is a class-based, object-oriented, statically typed language that runs on the Java Virtual Machine. Every program has a class with a public static void main entry point. It has strong collections like List, Map and Set, generics, interfaces and exceptions. For web backends, Spring Boot is the common framework: annotated controllers map HTTP routes to methods that return data, often JSON.`,
    ],
    snippets: [
      { title: 'Java basics', code: `public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello, world");\n  }\n}` },
      { title: 'Spring Boot REST controller', code: `@RestController\npublic class HelloController {\n  @GetMapping("/api/hello")\n  public String hello() {\n    return "Hello from Spring";\n  }\n}` },
    ],
  },
  native: {
    concepts: [
      `React Native builds native mobile apps for iOS and Android from React components that map to native views. Instead of div and span you use View and Text, and Image for pictures; styling uses JavaScript objects via StyleSheet, similar to CSS. Navigation between screens is usually handled by React Navigation. The same React ideas apply: components, props, state and hooks.`,
    ],
    snippets: [
      { title: 'React Native screen', code: `import { View, Text, StyleSheet } from 'react-native';\n\nexport default function Home() {\n  return (\n    <View style={styles.center}>\n      <Text>Hello mobile</Text>\n    </View>\n  );\n}\nconst styles = StyleSheet.create({\n  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },\n});` },
    ],
  },
  website: {
    concepts: [
      `Building a website combines HTML for structure, CSS for style and JavaScript for behavior. A simple static site is three files: index.html links style.css and app.js. For a dynamic app you add a build tool like Vite and a framework like React, and optionally a Node or Express backend that serves the files and a JSON API. The frontend talks to the backend with fetch.`,
      `To go live, you deploy. Static sites and frontend apps host well on Vercel, Netlify or GitHub Pages: connect the git repository, set the build command and the output folder, and it publishes on push. A Node backend runs as a server or serverless function. Good practice: a responsive mobile-first layout, semantic HTML, a meta description and title for SEO, and fast, optimized images.`,
      `A typical project structure: index.html at the root, a src folder for components and logic, a public or assets folder for images, a style or css file, and package.json for scripts and dependencies. Keep concerns separated, reuse components, and test in the browser as you build.`,
    ],
    snippets: [
      { title: 'Minimal static website (3 files)', code: `<!-- index.html -->\n<!doctype html>\n<html lang="en"><head>\n  <meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title>Starter</title><link rel="stylesheet" href="style.css" />\n</head><body>\n  <h1>Hello</h1><button id="go">Click</button>\n  <script src="app.js"></script>\n</body></html>\n\n/* style.css */\nbody { font-family: system-ui; max-width: 720px; margin: 40px auto; }\nbutton { padding: 8px 16px; }\n\n// app.js\ndocument.querySelector('#go').addEventListener('click', () => alert('Hi'));` },
      { title: 'Responsive landing page (HTML + CSS grid)', code: `<main class="wrap">\n  <h1>Welcome</h1>\n  <section class="features">\n    <div class="card">Fast</div>\n    <div class="card">Simple</div>\n    <div class="card">Free</div>\n  </section>\n</main>\n<style>\n.wrap { max-width: 960px; margin: 0 auto; padding: 24px; }\n.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 16px; }\n.card { padding: 24px; border: 1px solid #ddd; border-radius: 12px; }\n</style>` },
    ],
  },
  typescript: {
    concepts: [
      `TypeScript is JavaScript with static types: you annotate variables, parameters and return values, and the compiler catches type errors before the code runs. Common types are string, number, boolean, arrays like string[], objects, union types with a pipe, and any to opt out. Interfaces and type aliases describe object shapes. It compiles to plain JavaScript and powers most modern React and Node projects.`,
    ],
    snippets: [
      { title: 'TypeScript types + interface', code: `interface User {\n  id: number;\n  name: string;\n  admin?: boolean;\n}\nfunction greet(u: User): string {\n  return 'Hi ' + u.name;\n}` },
      { title: 'Typed React component', code: `import { useState } from 'react';\n\ntype Props = { title: string };\nexport default function Box({ title }: Props) {\n  const [open, setOpen] = useState<boolean>(false);\n  return <button onClick={() => setOpen(!open)}>{title}</button>;\n}` },
    ],
  },
  sql: {
    concepts: [
      `SQL, Structured Query Language, manages relational databases. Tables hold rows and columns. SELECT reads data, INSERT adds rows, UPDATE changes them, DELETE removes them, and WHERE filters. JOIN combines tables on a shared key. Most web apps store users, posts and orders in a database like PostgreSQL, MySQL or SQLite, and the backend runs these queries on the server.`,
    ],
    snippets: [
      { title: 'Create a table and query it', code: `CREATE TABLE users (\n  id SERIAL PRIMARY KEY,\n  name TEXT NOT NULL,\n  email TEXT UNIQUE\n);\nINSERT INTO users (name, email) VALUES ('Ada', 'ada@example.com');\nSELECT * FROM users WHERE name = 'Ada';` },
      { title: 'Join two tables', code: `SELECT u.name, o.total\nFROM orders o\nJOIN users u ON u.id = o.user_id\nWHERE o.total > 100;` },
    ],
  },
  git: {
    concepts: [
      `Git is a version control system that tracks changes to code. You stage changes with git add, save them with git commit, and sync with a remote like GitHub using git push and git pull. Branches let you build features in isolation, then merge them. A common flow is: clone a repository, create a branch, commit your work, open a pull request, and merge it.`,
    ],
    snippets: [
      { title: 'Everyday Git commands', code: `git clone <url>\ngit checkout -b feature\ngit add .\ngit commit -m 'Add feature'\ngit push -u origin feature` },
      { title: 'Branching, merging, rebasing', code: `git branch feature\ngit switch feature\ngit switch main\ngit merge feature        # combine feature into main\ngit rebase main          # replay your commits on top of main\ngit log --oneline --graph` },
    ],
  },
  api: {
    concepts: [
      `A REST API exposes data over HTTP using methods: GET reads, POST creates, PUT or PATCH updates, and DELETE removes. Resources live at URLs like /api/users and /api/users/1. Servers respond with JSON and status codes: 200 ok, 201 created, 400 bad request, 401 unauthorized, 404 not found, 500 server error. The frontend talks to the API with fetch and renders the result.`,
    ],
    snippets: [
      { title: 'REST endpoints with Express', code: `app.get('/api/posts', (req, res) => res.json(posts));\napp.get('/api/posts/:id', (req, res) =>\n  res.json(posts.find((p) => p.id == req.params.id)),\n);\napp.post('/api/posts', (req, res) => {\n  posts.push(req.body);\n  res.status(201).json(req.body);\n});` },
    ],
  },
  database: {
    concepts: [
      `A database stores app data persistently. Relational databases (PostgreSQL, MySQL, SQLite) use tables, rows and SQL; NoSQL databases like MongoDB store flexible JSON-like documents. An ORM such as Prisma, or an ODM like Mongoose, lets you query the database from JavaScript with typed models instead of raw SQL. Web apps connect from the backend only, so credentials stay secret.`,
    ],
    snippets: [
      { title: 'Prisma schema + query', code: `model User {\n  id    Int    @id @default(autoincrement())\n  email String @unique\n  name  String?\n}\n\n// query\nconst users = await prisma.user.findMany({ where: { name: 'Ada' } });` },
      { title: 'MongoDB with Mongoose', code: `import mongoose from 'mongoose';\nconst User = mongoose.model('User', new mongoose.Schema({\n  name: String,\n  email: { type: String, unique: true },\n}));\nconst u = await User.create({ name: 'Ada', email: 'ada@example.com' });` },
    ],
  },
  auth: {
    concepts: [
      `Authentication proves who a user is; authorization controls what they may do. Common patterns: a session stored in a cookie, or a stateless JSON Web Token (JWT) sent in the Authorization header. Never store plain passwords — hash them with bcrypt. OAuth lets users sign in with Google or GitHub. Services like Supabase Auth or Auth0 handle sign-up, login and tokens, with row-level security on the database.`,
    ],
    snippets: [
      { title: 'Hash and verify a password (bcrypt)', code: `import bcrypt from 'bcryptjs';\nconst hash = await bcrypt.hash(password, 10);\nconst ok = await bcrypt.compare(input, hash);` },
      { title: 'Protect an Express route with JWT', code: `import jwt from 'jsonwebtoken';\nfunction auth(req, res, next) {\n  const token = req.headers.authorization?.split(' ')[1];\n  try {\n    req.user = jwt.verify(token, process.env.SECRET);\n    next();\n  } catch {\n    res.status(401).json({ error: 'unauthorized' });\n  }\n}` },
      { title: 'Supabase email sign-in', code: `import { createClient } from '@supabase/supabase-js';\nconst supabase = createClient(url, anonKey);\nawait supabase.auth.signInWithPassword({ email, password });` },
    ],
  },
  testing: {
    concepts: [
      `Tests check that code works and keep it working as it changes. Unit tests cover small functions; integration tests cover modules together; end-to-end (E2E) tests drive the real app in a browser. Vitest and Jest run unit tests with describe, it and expect assertions. Playwright and Cypress run E2E tests. Run the tests automatically in CI on every push so regressions are caught early.`,
    ],
    snippets: [
      { title: 'Unit test (Vitest / Jest)', code: `import { describe, it, expect } from 'vitest';\nimport { sum } from './math';\n\ndescribe('sum', () => {\n  it('adds numbers', () => {\n    expect(sum(2, 3)).toBe(5);\n  });\n});` },
      { title: 'End-to-end test (Playwright)', code: `import { test, expect } from '@playwright/test';\n\ntest('home page loads', async ({ page }) => {\n  await page.goto('http://localhost:3000');\n  await expect(page.getByRole('heading')).toBeVisible();\n});` },
    ],
  },
  animation: {
    concepts: [
      `Web animation brings interfaces to life. A CSS transition animates a property change over time; CSS keyframe animations define multi-step motion. For JavaScript-driven animation use requestAnimationFrame for smooth per-frame updates, or the Web Animations API. Libraries like Framer Motion (React) and GSAP make complex motion easy. Always respect prefers-reduced-motion for accessibility.`,
    ],
    snippets: [
      { title: 'CSS transition + keyframes', code: `.btn { transition: transform 0.2s ease; }\n.btn:hover { transform: scale(1.05); }\n\n@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }\n.card { animation: fadeIn 0.4s ease both; }` },
      { title: 'requestAnimationFrame loop', code: `let x = 0;\nfunction frame() {\n  x += 1;\n  box.style.transform = 'translateX(' + x + 'px)';\n  if (x < 200) requestAnimationFrame(frame);\n}\nrequestAnimationFrame(frame);` },
      { title: 'Framer Motion (React)', code: `import { motion } from 'framer-motion';\n\nexport default function Fade() {\n  return <motion.div animate={{ opacity: 1 }} initial={{ opacity: 0 }} transition={{ duration: 0.4 }} />;\n}` },
    ],
  },
};

// ── helpers ───────────────────────────────────────────────────────────────────
function htmlToText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

/** Sentence-boundary chunking for prose (mirrors web/src/lib/files.ts chunkText). */
function chunkProse(text, size = 420, max = 4) {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const parts = clean.split(/(?<=[.!?…])\s+/);
  const chunks = [];
  let buf = '';
  for (const p of parts) {
    if (buf && (buf + ' ' + p).length > size) {
      chunks.push(buf.trim());
      buf = p;
    } else {
      buf = buf ? `${buf} ${p}` : p;
    }
    if (chunks.length >= max) break;
  }
  if (buf && chunks.length < max) chunks.push(buf.trim());
  return chunks.slice(0, max);
}

async function fetchText(url, timeoutMs = 8000) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(url, { signal: ctrl.signal, headers: { 'user-agent': 'AuriBrainIngest/1' } });
    clearTimeout(t);
    if (!res.ok) return '';
    const html = await res.text();
    return htmlToText(html).slice(0, 5000);
  } catch {
    return '';
  }
}

/** Run an async fn over items with bounded concurrency (keeps the fetch fast). */
async function mapLimit(items, limit, fn) {
  const out = [];
  let i = 0;
  const run = async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, run));
  return out;
}

// ── main ──────────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const offline = args.includes('--offline');
  const outIdx = args.indexOf('--out');
  const outPath =
    outIdx >= 0 && args[outIdx + 1]
      ? resolve(process.cwd(), args[outIdx + 1])
      : resolve(HERE, '../src/brain/seed/programming.ingested.ts');

  const urlFor = (tech) => SOURCES.find((s) => s.tech === tech)?.url ?? '';
  const chunks = [];
  let prose = 0;
  let snips = 0;

  for (const [tech, body] of Object.entries(CORPUS)) {
    const source = urlFor(tech);
    for (const concept of body.concepts ?? []) {
      for (const c of chunkProse(concept)) {
        chunks.push({ tech, text: c, source });
        prose++;
      }
    }
    for (const s of body.snippets ?? []) {
      chunks.push({ tech, text: `${s.title}\n${s.code}`, source });
      snips++;
    }
  }

  // Best-effort: pull MANY official doc pages in parallel (skipped when --offline).
  let fetched = 0;
  if (!offline) {
    const results = await mapLimit(FETCH_URLS, 6, async ({ tech, url }) => ({
      tech,
      url,
      text: await fetchText(url),
    }));
    for (const { tech, url, text } of results) {
      for (const c of chunkProse(text, 420, 5)) {
        chunks.push({ tech, text: c, source: url });
        fetched++;
      }
    }
  }

  const header = `// programming.ingested.ts — GENERATED by AI-3's \`npm run ingest:brain\` script.
// DO NOT EDIT BY HAND. A large, curated, website-building-focused programming corpus
// (concepts → vocab/Markov; code snippets stored verbatim as 'doc' nodes with their
// source URL). AI-1's seedProgramming() uses these chunks when non-empty. Regenerate:
//   npm run ingest:brain            (curated + best-effort live docs)
//   npm run ingest:brain -- --offline   (curated only, deterministic)
// Runtime is offline + key-free; only THIS build script ever touches the network.

export const PROGRAMMING_SEED_VERSION = ${SEED_VERSION};

export interface ProgSource {
  tech: string;
  title: string;
  url: string;
  topics: string[];
}

export interface ProgChunk {
  tech: string;
  text: string;
  source: string;
}

export const PROGRAMMING_SOURCES: ProgSource[] = ${JSON.stringify(SOURCES, null, 2)};

export const PROGRAMMING_CHUNKS: ProgChunk[] = ${JSON.stringify(chunks, null, 2)};
`;

  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, header, 'utf8');

  console.log(
    `[ingest:brain] wrote ${chunks.length} chunks → ${outPath}\n` +
      `              prose: ${prose}, snippets: ${snips}, live: ${fetched}${offline ? ' (offline mode)' : ''}`,
  );
}

main().catch((e) => {
  console.error('[ingest:brain] failed:', e?.message ?? e);
  process.exit(1);
});
