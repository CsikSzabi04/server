// designSnippets.ts — working CSS / UI-design recipes (seed v18). Every snippet is
// ORIGINAL code written for Auri (licence: original); `source` is a reference to the
// official docs, not where the code was copied from. Appended to PROGRAMMING_SNIPPETS:
// findSnippet() answers "how to make a … in css" with them, the code chat gets them as
// grounding, and the 3D brain shows each one as a doc neuron on its hub (css / design /
// tailwind). `alt` = accent-free Hungarian stems that also match. No personal data:
// demo content is generic ("Card title", "you@example.com" never appears in learned text).
import type { ProgSnippet } from './programmingCurated';

const r = String.raw;
const MDN = 'https://developer.mozilla.org/en-US/docs/Web/CSS/';
const DESIGN = 'https://web.dev/learn/design/';
const TW = 'https://tailwindcss.com/docs/';

export const DESIGN_SNIPPETS: ProgSnippet[] = [
  // ── layout recipes ───────────────────────────────────────────────────────────
  { tech: 'css', title: 'Center anything with CSS grid (place-items)', alt: ['kozep', 'igazit'], code: r`.center {
  display: grid;
  place-items: center;
  min-height: 100dvh;
}`, source: `${MDN}place-items` },
  { tech: 'css', title: 'Centered content container with max-width', alt: ['kozep', 'tarolo', 'kontener'], code: r`.container {
  width: min(100% - 2rem, 72rem);
  margin-inline: auto;
}`, source: `${MDN}min` },
  { tech: 'css', title: 'Holy grail page layout with grid template areas', alt: ['elrendez', 'oldalsav', 'fejlec', 'lablec'], code: r`body {
  min-height: 100dvh;
  display: grid;
  grid-template:
    "header header" auto
    "nav    main"   1fr
    "footer footer" auto / 220px 1fr;
}
header { grid-area: header; }
nav    { grid-area: nav; }
main   { grid-area: main; }
footer { grid-area: footer; }
@media (width < 700px) {
  body { grid-template: "header" auto "main" 1fr "nav" auto "footer" auto / 1fr; }
}`, source: `${MDN}grid-template-areas` },
  { tech: 'css', title: 'Sticky footer layout (footer at the bottom)', alt: ['lablec', 'alja'], code: r`body {
  min-height: 100dvh;
  display: grid;
  grid-template-rows: auto 1fr auto; /* header, main, footer */
}`, source: `${MDN}grid-template-rows` },
  { tech: 'css', title: 'Sidebar layout that wraps on small screens', alt: ['oldalsav', 'elrendez'], code: r`.with-sidebar {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}
.with-sidebar > aside { flex: 1 1 240px; }
.with-sidebar > main  { flex: 999 1 60%; min-width: 0; }`, source: `${MDN}flex` },
  { tech: 'css', title: 'Responsive card grid with auto-fit and minmax', alt: ['kartya', 'racs', 'reszponziv'], code: r`.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
  gap: 1.5rem;
}`, source: `${MDN}repeat` },
  { tech: 'css', title: 'Bento grid layout (cards of different sizes)', alt: ['bento', 'racs', 'kartya'], code: r`.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: 160px;
  gap: 1rem;
}
.bento .big  { grid-column: span 2; grid-row: span 2; }
.bento .wide { grid-column: span 2; }
@media (width < 700px) { .bento { grid-template-columns: repeat(2, 1fr); } }`, source: `${MDN}grid-column` },
  { tech: 'css', title: 'Subgrid cards with aligned titles and buttons', alt: ['kartya', 'igazit'], code: r`.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.card {
  display: grid;
  grid-row: span 3;               /* image, text, button */
  grid-template-rows: subgrid;    /* share the parent's rows */
}`, source: `${MDN}CSS_grid_layout/Subgrid` },
  { tech: 'css', title: 'Stack layout spacing (owl selector)', alt: ['terkoz', 'egymas'], code: r`.stack > * + * {
  margin-block-start: var(--space, 1rem);
}`, source: `${MDN}Adjacent_sibling_combinator` },
  { tech: 'css', title: 'Cluster of tags or buttons that wraps (flex wrap gap)', alt: ['cimke', 'gomb', 'tordel'], code: r`.cluster {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}`, source: `${MDN}gap` },
  { tech: 'css', title: 'Full-bleed section inside a centered column', alt: ['teljes', 'szelesseg'], code: r`.content {
  display: grid;
  grid-template-columns: 1fr min(65ch, 100% - 2rem) 1fr;
}
.content > * { grid-column: 2; }
.content > .full-bleed { grid-column: 1 / -1; }`, source: `${MDN}grid-column` },
  { tech: 'css', title: 'Sticky header with blur', alt: ['fejlec', 'ragados'], code: r`.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(255 255 255 / 0.75);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgb(0 0 0 / 0.06);
}`, source: `${MDN}position` },
  { tech: 'css', title: 'Split hero section (text and image side by side)', alt: ['hero', 'nyito'], code: r`.hero {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  align-items: center;
  gap: clamp(2rem, 5vw, 5rem);
  padding-block: clamp(3rem, 8vw, 7rem);
}
@media (width < 800px) { .hero { grid-template-columns: 1fr; } }`, source: `${DESIGN}layout` },
  { tech: 'css', title: 'Equal height columns with flexbox', alt: ['oszlop', 'egyforma'], code: r`.row { display: flex; gap: 1rem; }
.row > * { flex: 1; } /* flex items stretch to the tallest by default */`, source: `${MDN}align-items` },
  { tech: 'css', title: 'Responsive video or iframe with aspect-ratio', alt: ['video', 'kepar'], code: r`.video {
  width: 100%;
  aspect-ratio: 16 / 9;
  border: 0;
}`, source: `${MDN}aspect-ratio` },

  // ── modern CSS ───────────────────────────────────────────────────────────────
  { tech: 'css', title: 'Container query card (responsive component)', alt: ['kontener', 'kartya', 'reszponziv'], code: r`.card-wrap { container-type: inline-size; }

.card { display: grid; gap: 1rem; }
@container (width > 420px) {
  .card { grid-template-columns: 160px 1fr; align-items: center; }
}`, source: `${MDN}CSS_containment/Container_queries` },
  { tech: 'css', title: 'Style a parent with the :has() selector', alt: ['szulo', 'szelektor'], code: r`/* cards that contain an image get a different layout */
.card:has(img) { grid-template-rows: 200px auto; }

/* highlight a form field row whose input is invalid */
.field:has(input:user-invalid) label { color: #dc2626; }`, source: `${MDN}:has` },
  { tech: 'css', title: 'Native CSS nesting example', alt: ['beagyaz'], code: r`.card {
  padding: 1.5rem;
  border-radius: 1rem;

  & h3 { margin: 0 0 0.5rem; }
  &:hover { box-shadow: 0 8px 24px rgb(0 0 0 / 0.08); }
  @media (width < 600px) { padding: 1rem; }
}`, source: `${MDN}CSS_nesting` },
  { tech: 'css', title: 'Cascade layers with @layer', alt: ['reteg'], code: r`@layer reset, base, components, utilities;

@layer base { a { color: var(--primary); } }
@layer components { .btn { padding: 0.6rem 1.1rem; } }
@layer utilities { .mt-0 { margin-top: 0; } } /* wins over components */`, source: `${MDN}@layer` },
  { tech: 'css', title: 'Fluid typography with clamp()', alt: ['betumeret', 'folyekony'], code: r`:root {
  --step-0: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --step-1: clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem);
  --step-2: clamp(1.6rem, 1.3rem + 1.3vw, 2.25rem);
  --step-3: clamp(2rem, 1.5rem + 2.4vw, 3.5rem);
}
body { font-size: var(--step-0); }
h1 { font-size: var(--step-3); }`, source: `${MDN}clamp` },
  { tech: 'css', title: 'Fluid spacing with clamp()', alt: ['terkoz', 'folyekony'], code: r`.section {
  padding-block: clamp(2.5rem, 6vw, 6rem);
  padding-inline: clamp(1rem, 4vw, 3rem);
}`, source: `${MDN}clamp` },
  { tech: 'css', title: 'Mix colors with color-mix()', alt: ['szin', 'kever'], code: r`.btn:hover {
  background: color-mix(in oklch, var(--primary), black 12%);
}
.badge {
  background: color-mix(in oklch, var(--primary) 15%, transparent);
}`, source: `${MDN}color_value/color-mix` },
  { tech: 'css', title: 'OKLCH color palette with CSS variables', alt: ['szin', 'paletta'], code: r`:root {
  --hue: 255;
  --primary-50:  oklch(0.97 0.02 var(--hue));
  --primary-200: oklch(0.88 0.07 var(--hue));
  --primary-500: oklch(0.62 0.19 var(--hue));
  --primary-700: oklch(0.48 0.17 var(--hue));
  --primary-900: oklch(0.30 0.10 var(--hue));
}`, source: `${MDN}color_value/oklch` },
  { tech: 'css', title: 'Balanced headings with text-wrap', alt: ['cim', 'tordel'], code: r`h1, h2, h3 { text-wrap: balance; }
p { text-wrap: pretty; } /* avoids a single word on the last line */`, source: `${MDN}text-wrap` },
  { tech: 'css', title: 'Style form controls with accent-color', alt: ['jelolo', 'urlap', 'szin'], code: r`:root { accent-color: #7c3aed; } /* checkboxes, radios, range, progress */`, source: `${MDN}accent-color` },
  { tech: 'css', title: 'View transition between pages (multi-page site)', alt: ['oldalvaltas', 'animacio'], code: r`@view-transition { navigation: auto; }

/* the logo morphs between pages */
.logo { view-transition-name: site-logo; }

::view-transition-old(root),
::view-transition-new(root) { animation-duration: 250ms; }`, source: `${MDN}@view-transition` },
  { tech: 'css', title: 'Reading progress bar with a scroll-driven animation', alt: ['gorget', 'csik', 'animacio'], code: r`.progress {
  position: fixed; inset: 0 0 auto 0; height: 4px;
  background: var(--primary);
  transform-origin: left;
  animation: grow linear both;
  animation-timeline: scroll(root);
}
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }`, source: `${MDN}animation-timeline` },
  { tech: 'css', title: 'Reveal on scroll with animation-timeline view()', alt: ['gorget', 'megjelen', 'animacio'], code: r`@supports (animation-timeline: view()) {
  .reveal {
    animation: reveal linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 30%;
  }
}
@keyframes reveal { from { opacity: 0; transform: translateY(24px); } }`, source: `${MDN}animation-timeline/view` },
  { tech: 'css', title: 'Entry animation with @starting-style', alt: ['belep', 'animacio'], code: r`.toast {
  transition: opacity 200ms, translate 200ms;
  @starting-style { opacity: 0; translate: 0 12px; }
}`, source: `${MDN}@starting-style` },
  { tech: 'css', title: 'Logical properties (margin-inline, padding-block)', alt: ['logikai'], code: r`.box {
  margin-inline: auto;        /* left + right */
  padding-block: 2rem;        /* top + bottom */
  border-inline-start: 4px solid var(--primary);
  inset-inline-end: 0;
}`, source: `${MDN}CSS_logical_properties_and_values` },

  // ── theming ──────────────────────────────────────────────────────────────────
  { tech: 'css', title: 'Dark mode with CSS variables and prefers-color-scheme', alt: ['sotet', 'tema'], code: r`:root {
  color-scheme: light dark;
  --bg: #ffffff;  --surface: #f6f7f9;
  --text: #16181d; --muted: #5b6170;
  --primary: #4f46e5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1115; --surface: #181b21;
    --text: #e8eaee; --muted: #a0a6b3;
    --primary: #8b85ff;
  }
}
body { background: var(--bg); color: var(--text); }`, source: `${MDN}@media/prefers-color-scheme` },
  { tech: 'design', title: 'Theme toggle with data-theme and localStorage', alt: ['sotet', 'tema', 'valt'], code: r`<button id="theme" aria-label="Toggle dark mode">🌓</button>
<script>
  const root = document.documentElement;
  const saved = localStorage.getItem('theme');
  if (saved) root.dataset.theme = saved;
  document.getElementById('theme').onclick = () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('theme', next);
  };
</script>
<style>
  :root[data-theme="dark"] { --bg: #0f1115; --text: #e8eaee; }
</style>`, source: `${DESIGN}theming` },
  { tech: 'design', title: 'Design tokens as CSS variables', alt: ['token', 'valtozo', 'rendszer'], code: r`:root {
  /* color */   --color-primary: #4f46e5; --color-text: #16181d; --color-muted: #5b6170;
  /* space */   --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px;
  /* radius */  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-full: 9999px;
  /* shadow */  --shadow-1: 0 1px 2px rgb(0 0 0 / .06); --shadow-2: 0 8px 24px rgb(0 0 0 / .08);
  /* type */    --font-sans: system-ui, sans-serif; --text-base: 1rem; --text-lg: 1.25rem;
  /* motion */  --ease-out: cubic-bezier(.2, .8, .2, 1); --dur-fast: 150ms;
}`, source: `${DESIGN}theming` },
  { tech: 'css', title: 'Modern CSS reset', alt: ['alap', 'reset'], code: r`*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; }
html { -webkit-text-size-adjust: none; text-size-adjust: none; }
body { line-height: 1.5; -webkit-font-smoothing: antialiased; }
img, picture, video, canvas, svg { display: block; max-width: 100%; }
input, button, textarea, select { font: inherit; }
p, h1, h2, h3, h4, h5, h6 { overflow-wrap: break-word; }`, source: `${MDN}box-sizing` },

  // ── typography ───────────────────────────────────────────────────────────────
  { tech: 'design', title: 'Readable body typography defaults', alt: ['betu', 'olvashato', 'tipografia'], code: r`body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 1.0625rem;  /* 17px */
  line-height: 1.6;
  color: #1f2328;
}
p, li { max-width: 65ch; }
h1, h2, h3 { line-height: 1.15; letter-spacing: -0.015em; }`, source: `${DESIGN}typography` },
  { tech: 'design', title: 'Type scale with a 1.25 ratio', alt: ['betumeret', 'skala'], code: r`:root {
  --text-sm: 0.8rem;    /* 12.8px */
  --text-base: 1rem;    /* 16px */
  --text-lg: 1.25rem;   /* 20px */
  --text-xl: 1.563rem;  /* 25px */
  --text-2xl: 1.953rem; /* 31px */
  --text-3xl: 2.441rem; /* 39px */
}`, source: `${DESIGN}typography` },
  { tech: 'css', title: 'Self-hosted web font with @font-face', alt: ['betutipus', 'font'], code: r`@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var.woff2") format("woff2");
  font-weight: 100 900;   /* variable font */
  font-display: swap;
}
body { font-family: "Inter", system-ui, sans-serif; }`, source: `${MDN}@font-face` },
  { tech: 'css', title: 'Gradient text', alt: ['szinatmenet', 'szoveg'], code: r`.gradient-text {
  background: linear-gradient(90deg, #6366f1, #ec4899);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}`, source: `${MDN}background-clip` },
  { tech: 'css', title: 'Truncate text with ellipsis (one line and multi-line)', alt: ['levag', 'harom', 'pont'], code: r`.one-line {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.three-lines {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}`, source: `${MDN}text-overflow` },
  { tech: 'css', title: 'Animated link underline on hover', alt: ['link', 'alahuz', 'animacio'], code: r`.link {
  text-decoration: none;
  background: linear-gradient(currentColor 0 0) left bottom / 0% 2px no-repeat;
  transition: background-size 250ms ease;
}
.link:hover, .link:focus-visible { background-size: 100% 2px; }`, source: `${MDN}background-size` },
  { tech: 'css', title: 'Custom text selection color', alt: ['kijeloles', 'szin'], code: r`::selection {
  background: #c7d2fe;
  color: #1e1b4b;
}`, source: `${MDN}::selection` },

  // ── colour, shadow, surface ──────────────────────────────────────────────────
  { tech: 'design', title: 'Layered soft shadow elevation scale', alt: ['arnyek', 'melyseg'], code: r`:root {
  --elev-1: 0 1px 2px rgb(16 24 40 / 0.06), 0 1px 3px rgb(16 24 40 / 0.08);
  --elev-2: 0 4px 8px -2px rgb(16 24 40 / 0.08), 0 2px 4px -2px rgb(16 24 40 / 0.06);
  --elev-3: 0 12px 24px -4px rgb(16 24 40 / 0.10), 0 4px 8px -4px rgb(16 24 40 / 0.06);
  --elev-4: 0 24px 48px -12px rgb(16 24 40 / 0.18);
}
.card { box-shadow: var(--elev-1); }
.card:hover { box-shadow: var(--elev-3); }`, source: `${MDN}box-shadow` },
  { tech: 'design', title: 'Glassmorphism card (frosted glass)', alt: ['uveg', 'kartya', 'atlatszo'], code: r`.glass {
  background: rgb(255 255 255 / 0.12);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgb(0 0 0 / 0.18);
  padding: 1.5rem;
}
@supports not (backdrop-filter: blur(1px)) {
  .glass { background: rgb(30 30 40 / 0.9); }
}`, source: `${MDN}backdrop-filter` },
  { tech: 'design', title: 'Neumorphism soft UI button', alt: ['gomb', 'puha'], code: r`body { background: #e6e9ef; }
.neu {
  background: #e6e9ef;
  border: none;
  border-radius: 16px;
  padding: 1rem 1.5rem;
  box-shadow: 8px 8px 16px #c5c9d0, -8px -8px 16px #ffffff;
}
.neu:active {
  box-shadow: inset 6px 6px 12px #c5c9d0, inset -6px -6px 12px #ffffff;
}`, source: `${MDN}box-shadow` },
  { tech: 'design', title: 'Mesh gradient background', alt: ['hatter', 'szinatmenet'], code: r`.mesh {
  background:
    radial-gradient(at 20% 20%, #a78bfa 0, transparent 50%),
    radial-gradient(at 80% 10%, #38bdf8 0, transparent 45%),
    radial-gradient(at 70% 80%, #f472b6 0, transparent 50%),
    #0f172a;
}`, source: `${MDN}gradient/radial-gradient` },
  { tech: 'css', title: 'Smooth gradient background in oklch', alt: ['szinatmenet', 'hatter'], code: r`.hero {
  background: linear-gradient(in oklch 135deg, #6366f1, #ec4899);
}`, source: `${MDN}gradient/linear-gradient` },
  { tech: 'design', title: 'Gradient border with background-clip', alt: ['keret', 'szinatmenet'], code: r`.gradient-border {
  border: 2px solid transparent;
  border-radius: 16px;
  background:
    linear-gradient(var(--surface, #fff), var(--surface, #fff)) padding-box,
    linear-gradient(135deg, #6366f1, #ec4899) border-box;
}`, source: `${MDN}background-clip` },
  { tech: 'design', title: 'Subtle noise grain texture overlay', alt: ['textura', 'szemcse'], code: r`.grain::after {
  content: "";
  position: absolute; inset: 0;
  pointer-events: none;
  opacity: 0.08;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='.8'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}`, source: `${MDN}::after` },
  { tech: 'design', title: 'Image with dark gradient overlay for readable text', alt: ['kep', 'szoveg', 'atfedes'], code: r`.cover {
  position: relative;
  color: #fff;
  background:
    linear-gradient(to top, rgb(0 0 0 / 0.7), transparent 60%),
    url("hero.jpg") center / cover;
  min-height: 60vh;
  display: grid;
  align-content: end;
  padding: 2rem;
}`, source: `${MDN}background` },

  // ── components ───────────────────────────────────────────────────────────────
  { tech: 'design', title: 'Primary button with hover, active and focus states', alt: ['gomb', 'allapot'], code: r`.btn {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.65rem 1.1rem;
  min-height: 44px;
  border: none; border-radius: 10px;
  background: var(--primary, #4f46e5);
  color: #fff; font-weight: 600;
  cursor: pointer;
  transition: background 150ms, transform 150ms, box-shadow 150ms;
}
.btn:hover { background: color-mix(in oklch, var(--primary, #4f46e5), black 12%); }
.btn:active { transform: translateY(1px); }
.btn:focus-visible { outline: 3px solid color-mix(in oklch, var(--primary, #4f46e5), white 40%); outline-offset: 2px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }`, source: `${DESIGN}interaction` },
  { tech: 'design', title: 'Outline and ghost secondary buttons', alt: ['gomb', 'masodlagos'], code: r`.btn-outline {
  background: transparent;
  color: var(--primary);
  border: 1.5px solid currentColor;
}
.btn-ghost {
  background: transparent;
  color: var(--text);
  border: none;
}
.btn-ghost:hover { background: rgb(0 0 0 / 0.05); }`, source: `${DESIGN}interaction` },
  { tech: 'design', title: 'Loading button with spinner', alt: ['gomb', 'toltes', 'porgo'], code: r`.btn[aria-busy="true"] { color: transparent; position: relative; pointer-events: none; }
.btn[aria-busy="true"]::after {
  content: ""; position: absolute; inset: 0; margin: auto;
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid #fff; border-right-color: transparent;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { rotate: 1turn; } }`, source: `${MDN}animation` },
  { tech: 'design', title: 'Card component with hover lift', alt: ['kartya', 'emel'], code: r`.card {
  background: var(--surface, #fff);
  border: 1px solid rgb(0 0 0 / 0.06);
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.06);
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgb(0 0 0 / 0.10);
}
.card img { width: 100%; aspect-ratio: 16 / 10; object-fit: cover; border-radius: 10px; }`, source: `${DESIGN}ui-patterns` },
  { tech: 'design', title: 'Whole card clickable with a stretched link', alt: ['kartya', 'kattint', 'link'], code: r`.card { position: relative; }
.card a.card-link::after {
  content: "";
  position: absolute;
  inset: 0;   /* the link covers the whole card */
}
.card:has(a:focus-visible) { outline: 3px solid var(--primary); }`, source: `${MDN}inset` },
  { tech: 'design', title: 'Pricing card highlight (most popular plan)', alt: ['ar', 'csomag', 'kartya'], code: r`.plans { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; align-items: center; }
.plan { padding: 2rem; border: 1px solid #e5e7eb; border-radius: 16px; }
.plan.popular {
  border: 2px solid var(--primary);
  transform: scale(1.04);
  box-shadow: 0 20px 40px -12px rgb(79 70 229 / 0.35);
  position: relative;
}
.plan.popular::before {
  content: "Most popular";
  position: absolute; top: -12px; left: 50%; translate: -50% 0;
  background: var(--primary); color: #fff;
  font-size: 0.75rem; padding: 0.2rem 0.7rem; border-radius: 999px;
}`, source: `${DESIGN}ui-patterns` },
  { tech: 'design', title: 'Badge and pill tag', alt: ['cimke', 'jelveny'], code: r`.badge {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem; font-weight: 600;
  background: color-mix(in oklch, var(--primary) 14%, transparent);
  color: var(--primary);
}`, source: `${MDN}border-radius` },
  { tech: 'design', title: 'Avatar circle with initials fallback', alt: ['profilkep', 'kor'], code: r`.avatar {
  width: 40px; aspect-ratio: 1;
  border-radius: 50%;
  object-fit: cover;
  display: grid; place-items: center;
  background: #e0e7ff; color: #3730a3;
  font-weight: 700; font-size: 0.9rem;
}`, source: `${MDN}object-fit` },
  { tech: 'design', title: 'Text input with label and focus ring', alt: ['mezo', 'urlap', 'bevitel'], code: r`<label class="field">
  <span>Project name</span>
  <input type="text" name="project" autocomplete="off" />
</label>
<style>
  .field { display: grid; gap: 0.35rem; font-weight: 500; }
  .field input {
    padding: 0.65rem 0.8rem;
    border: 1px solid #d0d5dd; border-radius: 10px;
    font: inherit;
    transition: border-color 150ms, box-shadow 150ms;
  }
  .field input:focus-visible {
    outline: none;
    border-color: var(--primary, #4f46e5);
    box-shadow: 0 0 0 4px rgb(79 70 229 / 0.18);
  }
</style>`, source: `${DESIGN}forms` },
  { tech: 'design', title: 'Show form errors only after the user typed (:user-invalid)', alt: ['hiba', 'urlap', 'valid'], code: r`input:user-invalid {
  border-color: #dc2626;
  box-shadow: 0 0 0 3px rgb(220 38 38 / 0.15);
}
input:user-invalid + .error { display: block; }
.error { display: none; color: #dc2626; font-size: 0.85rem; }`, source: `${MDN}:user-invalid` },
  { tech: 'design', title: 'Toggle switch from a checkbox', alt: ['kapcsolo', 'valt'], code: r`<input type="checkbox" class="switch" role="switch" aria-label="Notifications" />
<style>
  .switch {
    appearance: none;
    width: 44px; height: 26px; border-radius: 999px;
    background: #cbd5e1; position: relative; cursor: pointer;
    transition: background 200ms;
  }
  .switch::before {
    content: ""; position: absolute; top: 3px; left: 3px;
    width: 20px; height: 20px; border-radius: 50%; background: #fff;
    transition: translate 200ms;
  }
  .switch:checked { background: var(--primary, #4f46e5); }
  .switch:checked::before { translate: 18px 0; }
</style>`, source: `${MDN}appearance` },
  { tech: 'design', title: 'Accordion with details and summary', alt: ['lenyilo', 'harmonika', 'gyik'], code: r`<details class="faq">
  <summary>How does it work?</summary>
  <p>Answer text goes here.</p>
</details>
<style>
  .faq { border-bottom: 1px solid #e5e7eb; padding: 1rem 0; }
  .faq summary { cursor: pointer; font-weight: 600; list-style: none; display: flex; justify-content: space-between; }
  .faq summary::after { content: "+"; transition: rotate 200ms; }
  .faq[open] summary::after { rotate: 45deg; }
</style>`, source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/details' },
  { tech: 'design', title: 'Modal dialog with the dialog element and backdrop', alt: ['felugro', 'ablak', 'modal'], code: r`<dialog id="dlg">
  <h2>Delete project?</h2>
  <p>This cannot be undone.</p>
  <form method="dialog"><button>Cancel</button> <button value="ok">Delete</button></form>
</dialog>
<button onclick="dlg.showModal()">Open</button>
<style>
  dialog { border: none; border-radius: 16px; padding: 1.5rem; max-width: 420px;
           box-shadow: 0 24px 60px rgb(0 0 0 / 0.25); }
  dialog::backdrop { background: rgb(15 17 21 / 0.55); backdrop-filter: blur(3px); }
</style>`, source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog' },
  { tech: 'design', title: 'Tooltip with a pseudo-element', alt: ['sugo', 'tipp'], code: r`[data-tip] { position: relative; }
[data-tip]:hover::after, [data-tip]:focus-visible::after {
  content: attr(data-tip);
  position: absolute; bottom: calc(100% + 8px); left: 50%; translate: -50% 0;
  background: #111827; color: #fff;
  font-size: 0.75rem; white-space: nowrap;
  padding: 0.3rem 0.55rem; border-radius: 6px;
}`, source: `${MDN}attr` },
  { tech: 'design', title: 'Popover menu with the popover attribute', alt: ['menu', 'felugro'], code: r`<button popovertarget="menu">Menu</button>
<div id="menu" popover>
  <a href="#">Profile</a><a href="#">Settings</a><a href="#">Sign out</a>
</div>
<style>
  [popover] { border: 1px solid #e5e7eb; border-radius: 12px; padding: 0.5rem; }
  [popover] a { display: block; padding: 0.5rem 0.75rem; border-radius: 8px; }
  [popover] a:hover { background: #f3f4f6; }
</style>`, source: 'https://developer.mozilla.org/en-US/docs/Web/API/Popover_API' },
  { tech: 'design', title: 'Responsive navbar with hamburger menu', alt: ['navigacio', 'menu', 'hamburger'], code: r`<header class="nav">
  <a class="logo" href="/">Brand</a>
  <button class="burger" aria-expanded="false" aria-controls="links">☰</button>
  <nav id="links"><a href="#">Features</a><a href="#">Pricing</a><a href="#">Contact</a></nav>
</header>
<style>
  .nav { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.5rem; }
  .nav nav { display: flex; gap: 1.5rem; }
  .burger { display: none; }
  @media (width < 700px) {
    .burger { display: block; }
    .nav nav { display: none; position: absolute; inset: 64px 0 auto; flex-direction: column;
               background: var(--bg, #fff); padding: 1rem 1.5rem; }
    .nav nav.open { display: flex; }
  }
</style>
<script>
  const b = document.querySelector('.burger'), n = document.getElementById('links');
  b.onclick = () => b.setAttribute('aria-expanded', n.classList.toggle('open'));
</script>`, source: `${DESIGN}ui-patterns` },
  { tech: 'design', title: 'Tabs with an active indicator', alt: ['ful', 'valt'], code: r`.tabs { display: flex; gap: 0.25rem; border-bottom: 1px solid #e5e7eb; }
.tab {
  padding: 0.6rem 1rem; background: none; border: none; cursor: pointer;
  color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.tab[aria-selected="true"] { color: var(--primary); border-bottom-color: currentColor; font-weight: 600; }`, source: `${DESIGN}ui-patterns` },
  { tech: 'design', title: 'Skeleton loading placeholder with shimmer', alt: ['toltes', 'helykitolto', 'csontvaz'], code: r`.skeleton {
  border-radius: 8px;
  background: linear-gradient(90deg, #eceff3 25%, #f6f7f9 37%, #eceff3 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer { from { background-position: 100% 0; } to { background-position: 0 0; } }
@media (prefers-reduced-motion: reduce) { .skeleton { animation: none; } }`, source: `${MDN}animation` },
  { tech: 'design', title: 'CSS spinner loader', alt: ['toltes', 'porgo'], code: r`.spinner {
  width: 32px; aspect-ratio: 1; border-radius: 50%;
  border: 3px solid rgb(0 0 0 / 0.1);
  border-top-color: var(--primary, #4f46e5);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { rotate: 1turn; } }`, source: `${MDN}@keyframes` },
  { tech: 'design', title: 'Progress bar', alt: ['folyamat', 'csik'], code: r`<progress value="60" max="100"></progress>
<style>
  progress { width: 100%; height: 8px; border-radius: 999px; overflow: hidden;
             accent-color: var(--primary, #4f46e5); }
</style>`, source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/progress' },
  { tech: 'design', title: 'Toast notification', alt: ['ertesites', 'uzenet'], code: r`.toast {
  position: fixed; bottom: 1.5rem; right: 1.5rem;
  display: flex; gap: 0.75rem; align-items: center;
  padding: 0.85rem 1rem; border-radius: 12px;
  background: #111827; color: #f9fafb;
  box-shadow: 0 12px 32px rgb(0 0 0 / 0.25);
  animation: toast-in 250ms cubic-bezier(.2, .8, .2, 1);
}
@keyframes toast-in { from { opacity: 0; translate: 0 12px; } }`, source: `${MDN}animation` },
  { tech: 'design', title: 'Breadcrumb navigation', alt: ['morzsa', 'navigacio'], code: r`<nav aria-label="Breadcrumb"><ol class="crumbs">
  <li><a href="/">Home</a></li><li><a href="/docs">Docs</a></li><li aria-current="page">CSS</li>
</ol></nav>
<style>
  .crumbs { display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; padding: 0; color: #6b7280; }
  .crumbs li + li::before { content: "/"; margin-right: 0.5rem; opacity: 0.5; }
  .crumbs [aria-current] { color: inherit; font-weight: 600; }
</style>`, source: `${DESIGN}ui-patterns` },
  { tech: 'design', title: 'Divider line with text in the middle', alt: ['elvalaszto', 'vonal'], code: r`.divider {
  display: flex; align-items: center; gap: 1rem;
  color: #9ca3af; font-size: 0.85rem;
}
.divider::before, .divider::after {
  content: ""; flex: 1; height: 1px; background: currentColor; opacity: 0.4;
}`, source: `${MDN}::before` },
  { tech: 'design', title: 'Footer with link columns', alt: ['lablec', 'oszlop'], code: r`.footer {
  display: grid;
  grid-template-columns: 2fr repeat(3, 1fr);
  gap: 2rem;
  padding: 3rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  color: #6b7280;
}
.footer h4 { color: var(--text); font-size: 0.9rem; margin-bottom: 0.75rem; }
@media (width < 700px) { .footer { grid-template-columns: 1fr 1fr; } }`, source: `${DESIGN}layout` },
  { tech: 'design', title: 'Testimonial quote card', alt: ['velemeny', 'idezet'], code: r`.quote {
  padding: 1.75rem; border-radius: 16px; background: var(--surface, #f9fafb);
  font-size: 1.1rem; line-height: 1.6;
}
.quote::before { content: "“"; font-size: 3rem; line-height: 0; vertical-align: -0.4em; color: var(--primary); }
.quote footer { margin-top: 1rem; font-size: 0.9rem; color: #6b7280; }`, source: `${DESIGN}typography` },
  { tech: 'design', title: 'Feature list with check icons', alt: ['lista', 'pipa', 'elony'], code: r`.features { list-style: none; padding: 0; display: grid; gap: 0.6rem; }
.features li { display: flex; gap: 0.6rem; align-items: start; }
.features li::before {
  content: "✓"; flex: none;
  width: 1.4rem; aspect-ratio: 1; border-radius: 50%;
  display: grid; place-items: center; font-size: 0.8rem;
  background: #dcfce7; color: #15803d;
}`, source: `${MDN}::before` },
  { tech: 'design', title: 'Sticky table header and zebra rows', alt: ['tablazat', 'fejlec'], code: r`.table-wrap { max-height: 420px; overflow: auto; border: 1px solid #e5e7eb; border-radius: 12px; }
table { width: 100%; border-collapse: collapse; }
th { position: sticky; top: 0; background: #f9fafb; text-align: left; }
th, td { padding: 0.65rem 0.9rem; border-bottom: 1px solid #f0f1f3; }
tbody tr:nth-child(even) { background: #fcfcfd; }
tbody tr:hover { background: #f3f4f6; }`, source: `${MDN}position` },

  // ── effects & motion ─────────────────────────────────────────────────────────
  { tech: 'css', title: 'Fade in and slide up keyframes animation', alt: ['megjelen', 'animacio', 'beuszik'], code: r`@keyframes fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: none; }
}
.fade-up { animation: fade-up 500ms cubic-bezier(.2, .8, .2, 1) both; }
.fade-up:nth-child(2) { animation-delay: 80ms; }
.fade-up:nth-child(3) { animation-delay: 160ms; }`, source: `${MDN}@keyframes` },
  { tech: 'css', title: 'Image zoom on hover', alt: ['kep', 'nagyit'], code: r`.thumb { overflow: hidden; border-radius: 12px; }
.thumb img { transition: scale 400ms ease; }
.thumb:hover img { scale: 1.06; }`, source: `${MDN}scale` },
  { tech: 'css', title: 'Respect prefers-reduced-motion', alt: ['mozgas', 'akadalymentes'], code: r`@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}`, source: `${MDN}@media/prefers-reduced-motion` },
  { tech: 'css', title: 'Visible keyboard focus with :focus-visible', alt: ['fokusz', 'akadalymentes'], code: r`:focus-visible {
  outline: 3px solid var(--primary, #4f46e5);
  outline-offset: 3px;
  border-radius: 4px;
}`, source: `${MDN}:focus-visible` },
  { tech: 'css', title: 'Smooth scrolling with sticky header offset', alt: ['gorget', 'sima'], code: r`html { scroll-behavior: smooth; }
section[id] { scroll-margin-top: 80px; } /* height of the sticky header */`, source: `${MDN}scroll-margin-top` },
  { tech: 'css', title: 'Scroll snap carousel', alt: ['korhinta', 'csuszka', 'gorget'], code: r`.carousel {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 80%;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  overscroll-behavior-x: contain;
}
.carousel > * { scroll-snap-align: start; }`, source: `${MDN}scroll-snap-type` },
  { tech: 'css', title: 'Thin custom scrollbar', alt: ['gorgetosav'], code: r`.scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(0 0 0 / 0.3) transparent;
}`, source: `${MDN}scrollbar-color` },
  { tech: 'css', title: 'Object-fit cover thumbnails with aspect-ratio', alt: ['kep', 'kepar', 'kitolt'], code: r`.thumb {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 12px;
}`, source: `${MDN}object-fit` },
  { tech: 'css', title: 'Hover lift with transform and shadow transition', alt: ['emel', 'hover', 'animacio'], code: r`.lift {
  transition: transform 180ms cubic-bezier(.2, .8, .2, 1), box-shadow 180ms;
}
.lift:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 30px -10px rgb(0 0 0 / 0.25);
}`, source: `${MDN}transition` },
  { tech: 'css', title: 'Print styles', alt: ['nyomtat'], code: r`@media print {
  nav, footer, .no-print { display: none; }
  body { color: #000; background: #fff; font-size: 12pt; }
  a[href^="http"]::after { content: " (" attr(href) ")"; }
}`, source: `${MDN}@media` },

  // ── Tailwind versions of the same ideas ──────────────────────────────────────
  { tech: 'tailwind', title: 'Tailwind card with hover lift', alt: ['kartya'], code: r`<div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-1 hover:shadow-lg dark:bg-gray-900 dark:ring-white/10">
  <h3 class="text-lg font-semibold">Card title</h3>
  <p class="mt-2 text-gray-600 dark:text-gray-400">Short description.</p>
</div>`, source: `${TW}box-shadow` },
  { tech: 'tailwind', title: 'Tailwind primary button with focus ring', alt: ['gomb'], code: r`<button class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 font-semibold text-white hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50">
  Save changes
</button>`, source: `${TW}hover-focus-and-other-states` },
  { tech: 'tailwind', title: 'Tailwind responsive navbar', alt: ['navigacio', 'menu'], code: r`<header class="sticky top-0 z-10 border-b border-black/5 bg-white/75 backdrop-blur">
  <nav class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
    <a href="/" class="font-bold">Brand</a>
    <div class="hidden gap-6 md:flex"><a href="#">Features</a><a href="#">Pricing</a></div>
  </nav>
</header>`, source: `${TW}responsive-design` },
  { tech: 'tailwind', title: 'Tailwind hero section with gradient', alt: ['hero', 'szinatmenet'], code: r`<section class="bg-gradient-to-br from-indigo-600 to-pink-500 px-6 py-24 text-center text-white">
  <h1 class="text-balance text-4xl font-bold tracking-tight md:text-6xl">Build faster</h1>
  <p class="mx-auto mt-4 max-w-xl text-lg text-white/80">One sentence about the value.</p>
  <a href="#" class="mt-8 inline-block rounded-full bg-white px-6 py-3 font-semibold text-indigo-700">Get started</a>
</section>`, source: `${TW}background-image` },
  { tech: 'tailwind', title: 'Tailwind responsive card grid', alt: ['kartya', 'racs'], code: r`<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
  <!-- cards -->
</div>`, source: `${TW}grid-template-columns` },
  { tech: 'tailwind', title: 'Tailwind glassmorphism panel', alt: ['uveg'], code: r`<div class="rounded-3xl border border-white/20 bg-white/10 p-6 shadow-2xl backdrop-blur-lg">
  Glass panel
</div>`, source: `${TW}backdrop-filter-blur` },
];
