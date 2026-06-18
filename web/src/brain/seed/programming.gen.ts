// programming.gen.ts — GENERATED-SHAPE corpus for the Programming region.
//
// ⚠️ This file matches the output shape of AI-3's `npm run ingest:brain` script
// (PROGRAMMING_SEED_VERSION + PROGRAMMING_SOURCES + PROGRAMMING_CHUNKS), so that
// script can REGENERATE it (live docs or --offline) without breaking any import.
// The version below is the hand-curated OFFLINE FALLBACK, so the Programming
// region works with no network and no ingest run.
//
// Hand-curated extras the ingest script does NOT produce (verbatim code snippets,
// Q→A, keyword set, findSnippet) live in ./programmingCurated.ts and must NOT be
// overwritten by the script.
import { SOURCES } from './sources';

/** Bump when the corpus shape/content changes. */
export const PROGRAMMING_SEED_VERSION = 3;

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

// The official source registry (reused from sources.ts to avoid duplication).
// AI-3's generator emits an equivalent inline array of the same shape.
export const PROGRAMMING_SOURCES: ProgSource[] = SOURCES;

// Concept chunks (several per technology) as the offline fallback. Each chunk
// feeds the learner's vocabulary + Markov model and becomes a doc node citing
// `source`. AI-3's ingest script can later replace these with live doc chunks.
export const PROGRAMMING_CHUNKS: ProgChunk[] = [
  // JavaScript
  { tech: 'javascript', text: 'JavaScript is the programming language of the web. Variables use let and const, and functions return values. Arrays have map, filter and reduce. A promise represents a future value, handled with async and await.', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript' },
  { tech: 'javascript', text: 'In JavaScript an object groups related values into key and value pairs. You loop with for and while, branch with if and else, and compare with triple equals to avoid type coercion.', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators' },
  { tech: 'javascript', text: 'A function can be declared or written as an arrow function. Closures let an inner function remember the variables of the outer function. The DOM lets scripts read and change the page.', source: 'https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model' },
  // Node.js
  { tech: 'node', text: 'Node.js runs JavaScript on the server. The http module creates a web server and the fs module reads and writes files. Code is split into modules imported with import or require.', source: 'https://nodejs.org/docs/latest/api/' },
  { tech: 'node', text: 'In Node you install packages with npm and list them in package.json. The event loop handles many requests without blocking, and streams process large data piece by piece.', source: 'https://docs.npmjs.com/' },
  // React
  { tech: 'react', text: 'React builds user interfaces from components. A component returns JSX. State lives in the useState hook and useEffect runs a side effect after render. Props pass data from a parent to a child.', source: 'https://react.dev/learn' },
  { tech: 'react', text: 'React re-renders a component when its state or props change. Lists need a stable key, events use onClick and onChange, and custom hooks share logic between components.', source: 'https://react.dev/reference/react' },
  // HTML
  { tech: 'html', text: 'HTML describes the structure of a page using elements such as div, p, a, img, form and input, with attributes and semantic tags for headings and sections.', source: 'https://developer.mozilla.org/en-US/docs/Web/HTML' },
  { tech: 'html', text: 'A page starts with a doctype, then a head with the title and meta tags, and a body with the visible content. Semantic tags like header, main, nav and footer describe meaning.', source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element' },
  // CSS
  { tech: 'css', text: 'CSS styles HTML. Flexbox and grid lay out elements, and selectors target by tag, class or id. To center content, a flex container with align items center and justify content center works well.', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS' },
  { tech: 'css', text: 'The box model has content, padding, border and margin. Media queries make a layout responsive, and CSS variables store reusable colours and sizes.', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_box_model' },
  // Tailwind
  { tech: 'tailwind', text: 'Tailwind CSS is a utility-first framework. You compose small classes such as flex, items-center, justify-center, p-4 and text-center directly in the markup instead of writing custom CSS.', source: 'https://tailwindcss.com/docs' },
  { tech: 'tailwind', text: 'Tailwind uses responsive prefixes like md and lg, state prefixes like hover and focus, and spacing and colour scales so the whole design stays consistent.', source: 'https://tailwindcss.com/docs/responsive-design' },
  // Bootstrap
  { tech: 'bootstrap', text: 'Bootstrap is a CSS framework with a responsive grid built from container, row and col classes, plus ready-made components like the navbar, buttons and cards.', source: 'https://getbootstrap.com/docs/' },
  { tech: 'bootstrap', text: 'Bootstrap ships utility classes for spacing, colour and display, and JavaScript components such as modals, dropdowns and tooltips that work out of the box.', source: 'https://getbootstrap.com/docs/5.3/components/' },
  // Java
  { tech: 'java', text: 'Java is an object-oriented language. Code lives in classes, the public static void main method is the entry point, and the JVM runs the compiled bytecode across platforms.', source: 'https://docs.oracle.com/en/java/javase/' },
  { tech: 'java', text: 'A Java class has fields and methods, objects are created with the new keyword, and interfaces and inheritance let different classes share a common shape.', source: 'https://docs.oracle.com/javase/tutorial/java/concepts/' },
  // React Native / native
  { tech: 'native', text: 'React Native builds mobile apps with React. View and Text are the basic building blocks, and components render to real native UI on Android and iOS.', source: 'https://reactnative.dev/docs/getting-started' },
  { tech: 'native', text: 'In React Native you style with a StyleSheet object, lay out with flexbox, and handle taps with onPress. Native apps can also be written in Kotlin for Android or Swift for iOS.', source: 'https://reactnative.dev/docs/style' },

  // ── deeper coverage for richer vocabulary + a brain that can build pages ──────
  // building a website end to end
  { tech: 'html', text: 'A website is built from three layers: HTML gives the structure and content, CSS gives the look and the layout, and JavaScript adds behaviour and interactivity. You start with an index.html file.', source: 'https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web' },
  { tech: 'html', text: 'A typical page layout has a header with a logo and a navigation menu, a hero section with a headline and a button, several content sections, and a footer with links and copyright.', source: 'https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Document_and_website_structure' },
  { tech: 'css', text: 'A responsive design adapts to the screen. Use a flexible container, a grid that wraps with repeat and auto-fit, relative units like rem and percent, and media queries for phone, tablet and desktop breakpoints.', source: 'https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design' },
  { tech: 'css', text: 'Position elements with static, relative, absolute, fixed or sticky. A sticky header stays at the top while scrolling. Transitions and transforms add smooth motion to hovers and menus.', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/position' },
  // JavaScript depth
  { tech: 'javascript', text: 'The DOM lets JavaScript find elements with querySelector, change their text and classes, and react to clicks with addEventListener. This is how a page becomes interactive.', source: 'https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelector' },
  { tech: 'javascript', text: 'Fetch data from an API with fetch, await the response, and parse JSON. Handle errors with try and catch, and show a loading state while the request is in flight.', source: 'https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch' },
  { tech: 'javascript', text: 'Modules split code into files that export and import values. Destructuring pulls fields out of objects and arrays, and the spread operator copies and merges them.', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules' },
  { tech: 'javascript', text: 'Common array methods are map to transform, filter to keep some items, find to get one, reduce to combine, and sort to order. They make data handling short and clear.', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array' },
  // React depth
  { tech: 'react', text: 'A React form keeps each input in state as a controlled component, reads values on change, and submits with an onSubmit handler that calls preventDefault first.', source: 'https://react.dev/reference/react-dom/components/form' },
  { tech: 'react', text: 'useEffect runs after render and can fetch data, set up a timer or subscribe to events; return a cleanup function to undo it. The dependency array decides when it runs again.', source: 'https://react.dev/reference/react/useEffect' },
  { tech: 'react', text: 'Share state without prop drilling using the Context API and useContext. For routing between pages in a single-page app, a router maps a URL path to a component.', source: 'https://react.dev/learn/passing-data-deeply-with-context' },
  // Node / backend depth
  { tech: 'node', text: 'A backend exposes routes: a path and a method like GET or POST map to a handler that returns data. Read the request body, validate it, and send a JSON response with a status code.', source: 'https://nodejs.org/docs/latest/api/http.html' },
  { tech: 'node', text: 'Keep secrets like API keys in environment variables, not in the code. Use async and await for file and network work so the server stays responsive under load.', source: 'https://nodejs.org/docs/latest/api/process.html' },
  // CSS layout depth
  { tech: 'css', text: 'Flexbox lays items in a row or column: justify-content spaces them along the main axis, align-items aligns them across it, and gap adds spacing without margins.', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout/Basic_concepts_of_flexbox' },
  { tech: 'css', text: 'CSS Grid builds two-dimensional layouts with rows and columns. grid-template-columns sets the tracks, and fr units share the free space between them.', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout' },
  // HTML depth
  { tech: 'html', text: 'Forms collect input with text, email, password, number, checkbox and select fields. Labels describe each field, and the required attribute asks the browser to validate it.', source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input' },
  // Java depth
  { tech: 'java', text: 'Java has primitive types like int, double and boolean, and reference types like String and arrays. Collections such as ArrayList and HashMap store groups of values.', source: 'https://docs.oracle.com/javase/tutorial/collections/' },
  { tech: 'java', text: 'Control flow in Java uses if and else, switch, and for and while loops. Methods take parameters and return a value, and exceptions are handled with try and catch.', source: 'https://docs.oracle.com/javase/tutorial/java/nutsandbolts/flow.html' },
  // Bootstrap depth
  { tech: 'bootstrap', text: 'Bootstrap layouts use a container, rows, and columns numbered to twelve. Breakpoints like col-md and col-lg change how many columns show on larger screens.', source: 'https://getbootstrap.com/docs/5.3/layout/grid/' },
  // deployment / general
  { tech: 'node', text: 'To put a site online you build it, then deploy the files to a host. Static pages go to GitHub Pages, Netlify or Vercel; a Node server can run on a small cloud instance or a platform.', source: 'https://vercel.com/docs' },
];
