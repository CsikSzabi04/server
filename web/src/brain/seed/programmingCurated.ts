// programmingCurated.ts — hand-curated Programming extras the ingest script does
// NOT generate (verbatim code snippets + Q→A + keyword set). Kept SEPARATE from
// programming.gen.ts (which AI-3's `npm run ingest:brain` may regenerate), so
// regeneration never clobbers these. Snippets are short, original idioms.
// The programming-LANGUAGES pack (C, C++, C#, .NET 10, Bash, Linux, …) is appended
// from ./languageSnippets.ts and ./languages.ts.
import { LANG_SNIPPETS } from './languageSnippets';
import { LANG_QA, LANG_KEYWORDS } from './languages';
import { DESIGN_SNIPPETS } from './designSnippets';
import { DESIGN_QA, DESIGN_KEYWORDS } from './design';
import { mentionsTech, normalizeTechQuery } from './techAlias';

export interface ProgSnippet {
  tech: string;
  title: string;
  code: string;
  source: string;
  /** Extra accent-free (Hungarian) word stems that also match, as word prefixes. */
  alt?: string[];
}
export interface ProgQA {
  tech: string;
  q: string;
  a: string;
}

// Short, original code idioms. Stored verbatim so they can be quoted/cited.
export const PROGRAMMING_SNIPPETS: ProgSnippet[] = [
  { tech: 'css', title: 'Center a div with flexbox', code: '.box {\n  display: flex;\n  align-items: center;\n  justify-content: center;\n}', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_flexible_box_layout' },
  { tech: 'css', title: 'Simple responsive grid', code: '.grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));\n}', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout' },
  { tech: 'react', title: 'useState counter', code: 'const [count, setCount] = useState(0);\nreturn <button onClick={() => setCount(count + 1)}>{count}</button>;', source: 'https://react.dev/reference/react/useState' },
  { tech: 'react', title: 'useEffect on mount', code: "useEffect(() => {\n  // runs once after the first render\n}, []);", source: 'https://react.dev/reference/react/useEffect' },
  { tech: 'node', title: 'Minimal HTTP server', code: "import { createServer } from 'node:http';\ncreateServer((req, res) => res.end('Hello')).listen(3000);", source: 'https://nodejs.org/docs/latest/api/http.html' },
  { tech: 'node', title: 'Read a file', code: "import { readFile } from 'node:fs/promises';\nconst text = await readFile('file.txt', 'utf8');", source: 'https://nodejs.org/docs/latest/api/fs.html' },
  { tech: 'javascript', title: 'Fetch JSON', code: 'const res = await fetch(url);\nconst data = await res.json();', source: 'https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API' },
  { tech: 'javascript', title: 'Map an array', code: 'const doubled = nums.map((n) => n * 2);', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map' },
  { tech: 'html', title: 'Basic form', code: '<form>\n  <input name="email" type="email" />\n  <button>Send</button>\n</form>', source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/form' },
  { tech: 'tailwind', title: 'Centered card', code: '<div class="flex items-center justify-center p-4">card</div>', source: 'https://tailwindcss.com/docs/flex' },
  { tech: 'bootstrap', title: 'Grid row and columns', code: '<div class="container"><div class="row"><div class="col">A</div></div></div>', source: 'https://getbootstrap.com/docs/5.3/layout/grid/' },
  { tech: 'java', title: 'Hello main method', code: 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Hello");\n  }\n}', source: 'https://docs.oracle.com/en/java/javase/' },
  { tech: 'native', title: 'React Native View + Text', code: "import { View, Text } from 'react-native';\nexport default () => (\n  <View><Text>Hi</Text></View>\n);", source: 'https://reactnative.dev/docs/intro-react' },
  { tech: 'javascript', title: 'Filter an array', code: 'const adults = people.filter((p) => p.age >= 18);', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter' },
  { tech: 'javascript', title: 'Loop over an array', code: 'for (const item of items) {\n  console.log(item);\n}', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...of' },
  { tech: 'react', title: 'Render a list with keys', code: '{items.map((item) => (\n  <li key={item.id}>{item.name}</li>\n))}', source: 'https://react.dev/learn/rendering-lists' },
  { tech: 'react', title: 'Controlled input', code: 'const [text, setText] = useState("");\n<input value={text} onChange={(e) => setText(e.target.value)} />', source: 'https://react.dev/reference/react-dom/components/input' },
  { tech: 'node', title: 'Read a JSON file in Node', code: "import { readFile } from 'node:fs/promises';\nconst cfg = JSON.parse(await readFile('config.json', 'utf8'));", source: 'https://nodejs.org/docs/latest/api/fs.html' },
  { tech: 'css', title: 'Space items in a row', code: '.row {\n  display: flex;\n  gap: 12px;\n  justify-content: space-between;\n}', source: 'https://developer.mozilla.org/en-US/docs/Web/CSS/gap' },
  { tech: 'html', title: 'Link and image', code: '<a href="/home">Home</a>\n<img src="logo.png" alt="Logo" />', source: 'https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a' },
  { tech: 'tailwind', title: 'Responsive grid', code: '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">...</div>', source: 'https://tailwindcss.com/docs/grid-template-columns' },
  { tech: 'java', title: 'A simple class', code: 'public class Point {\n  int x, y;\n  Point(int x, int y) { this.x = x; this.y = y; }\n}', source: 'https://docs.oracle.com/javase/tutorial/java/javaOO/' },
  // Python
  { tech: 'python', title: 'Read a file in Python', code: "with open('file.txt') as f:\n    text = f.read()", source: 'https://docs.python.org/3/tutorial/inputoutput.html' },
  { tech: 'python', title: 'HTTP GET in Python (requests)', code: 'import requests\nr = requests.get(url)\ndata = r.json()', source: 'https://requests.readthedocs.io/' },
  { tech: 'python', title: 'Python for loop', code: 'for item in items:\n    print(item)', source: 'https://docs.python.org/3/tutorial/controlflow.html' },
  { tech: 'python', title: 'Python function', code: 'def add(a, b):\n    return a + b', source: 'https://docs.python.org/3/tutorial/controlflow.html#defining-functions' },
  { tech: 'python', title: 'Python list comprehension', code: 'squares = [n * n for n in range(10)]', source: 'https://docs.python.org/3/tutorial/datastructures.html' },
  { tech: 'python', title: 'Python class', code: 'class Point:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y', source: 'https://docs.python.org/3/tutorial/classes.html' },
  { tech: 'python', title: 'Parse JSON in Python', code: 'import json\ndata = json.loads(text)', source: 'https://docs.python.org/3/library/json.html' },
  // Java
  { tech: 'java', title: 'Read a file in Java', code: 'String text = Files.readString(Path.of("file.txt"));', source: 'https://docs.oracle.com/en/java/javase/' },
  { tech: 'java', title: 'Java for loop', code: 'for (int i = 0; i < n; i++) {\n  System.out.println(i);\n}', source: 'https://docs.oracle.com/javase/tutorial/java/nutsandbolts/for.html' },
  { tech: 'java', title: 'Java list (ArrayList)', code: 'List<String> list = new ArrayList<>();\nlist.add("hello");', source: 'https://docs.oracle.com/javase/tutorial/collections/' },
  // Kotlin
  { tech: 'kotlin', title: 'Kotlin function', code: 'fun add(a: Int, b: Int) = a + b', source: 'https://kotlinlang.org/docs/functions.html' },
  { tech: 'kotlin', title: 'Kotlin data class', code: 'data class User(val name: String, val age: Int)', source: 'https://kotlinlang.org/docs/data-classes.html' },
  { tech: 'kotlin', title: 'Kotlin null safety', code: 'val len = name?.length ?: 0', source: 'https://kotlinlang.org/docs/null-safety.html' },
  // PHP
  { tech: 'php', title: 'Connect to MySQL in PHP (PDO)', code: "$pdo = new PDO('mysql:host=localhost;dbname=app', $user, $pass);", source: 'https://www.php.net/manual/en/book.pdo.php' },
  { tech: 'php', title: 'Run a query in PHP', code: "$stmt = $pdo->query('SELECT * FROM users');\n$rows = $stmt->fetchAll();", source: 'https://www.php.net/manual/en/pdo.query.php' },
  { tech: 'php', title: 'PHP echo a variable', code: '<?php echo "Hello, $name"; ?>', source: 'https://www.php.net/manual/en/function.echo.php' },
  // SQL / MySQL
  { tech: 'sql', title: 'SQL SELECT with WHERE', code: 'SELECT name, email FROM users WHERE active = 1 ORDER BY name;', source: 'https://dev.mysql.com/doc/refman/8.0/en/select.html' },
  { tech: 'sql', title: 'SQL JOIN two tables', code: 'SELECT o.id, u.name\nFROM orders o\nJOIN users u ON u.id = o.user_id;', source: 'https://dev.mysql.com/doc/refman/8.0/en/join.html' },
  { tech: 'sql', title: 'SQL INSERT', code: "INSERT INTO users (name, email) VALUES ('Ann', 'ann@example.com');", source: 'https://dev.mysql.com/doc/refman/8.0/en/insert.html' },
  { tech: 'sql', title: 'SQL CREATE TABLE', code: 'CREATE TABLE users (\n  id INT PRIMARY KEY,\n  name VARCHAR(100)\n);', source: 'https://dev.mysql.com/doc/refman/8.0/en/create-table.html' },
  // more JS / Node
  { tech: 'javascript', title: 'Sum an array with reduce', code: 'const sum = nums.reduce((a, b) => a + b, 0);', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/reduce' },
  { tech: 'javascript', title: 'Object destructuring', code: 'const { name, age } = user;', source: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment' },
  { tech: 'node', title: 'Express server', code: "import express from 'express';\nconst app = express();\napp.get('/', (req, res) => res.send('Hi'));\napp.listen(3000);", source: 'https://expressjs.com/en/starter/hello-world.html' },
  // programming-languages pack (seed v17): Python … C, C++, C#, .NET 10, Bash, Linux, Windows, iOS, VPN, WPS
  ...LANG_SNIPPETS,
  // CSS + visual design pack (seed v18): layouts, modern CSS, theming, components, motion
  ...DESIGN_SNIPPETS,
];

// Question→answer mappings (HU + EN) so respond()/qaCount cover common questions.
export const PROGRAMMING_QA: ProgQA[] = [
  { tech: 'css', q: 'how to center a div in css', a: 'Use a flex container: display:flex; align-items:center; justify-content:center;' },
  { tech: 'css', q: 'hogyan kell kozepre tenni egy div-et', a: 'Flexbox-szal: display:flex; align-items:center; justify-content:center;' },
  { tech: 'react', q: 'what is useeffect in react', a: 'A hook that runs a side effect after render; the dependency array controls when it runs.' },
  { tech: 'react', q: 'mi a useeffect a reactban', a: 'Egy hook, ami render utan mellekhatast futtat; a fuggoseg-tomb szabja meg, mikor fut.' },
  { tech: 'react', q: 'how to use state in react', a: 'Call useState to get a value and a setter: const [n, setN] = useState(0).' },
  { tech: 'node', q: 'how to create a server in node', a: 'Use the http module: createServer((req,res)=>...).listen(port).' },
  { tech: 'javascript', q: 'how to fetch json in javascript', a: 'Await fetch(url), then await res.json().' },
  { tech: 'java', q: 'what is the main method in java', a: 'public static void main(String[] args) is the entry point the JVM runs.' },
  { tech: 'tailwind', q: 'how to center with tailwind', a: 'Put flex items-center justify-center on the container element.' },
  { tech: 'bootstrap', q: 'how to make a grid in bootstrap', a: 'Use the container, row and col classes.' },
  { tech: 'native', q: 'how to show text in react native', a: 'Wrap the text in a Text component inside a View.' },
  { tech: 'javascript', q: 'what is a promise in javascript', a: 'An object that represents a future value; you handle it with then or with async and await.' },
  { tech: 'javascript', q: 'difference between let and const', a: 'let can be reassigned, const cannot; both are block scoped.' },
  { tech: 'javascript', q: 'how to loop over an array', a: 'Use for...of, or array methods like forEach and map.' },
  { tech: 'react', q: 'what is a component in react', a: 'A reusable piece of UI, written as a function that returns JSX.' },
  { tech: 'react', q: 'what are props in react', a: 'Read-only inputs passed from a parent component to a child.' },
  { tech: 'react', q: 'how to render a list in react', a: 'Map the array to elements and give each one a stable key prop.' },
  { tech: 'node', q: 'what is npm', a: 'The package manager for Node; it installs libraries and records them in package.json.' },
  { tech: 'node', q: 'how to read a file in node', a: 'Use fs/promises readFile with the path and an encoding like utf8.' },
  { tech: 'html', q: 'how to add a link in html', a: 'Use an anchor tag: <a href="url">text</a>.' },
  { tech: 'html', q: 'how to add an image in html', a: 'Use the img tag with a src and an alt attribute.' },
  { tech: 'css', q: 'what is the box model', a: 'Every element is content surrounded by padding, then border, then margin.' },
  { tech: 'java', q: 'what is a class in java', a: 'A blueprint with fields and methods from which you create objects with new.' },
  { tech: 'java', q: 'how to print in java', a: 'Use System.out.println to print a line to the console.' },
  // building websites end to end
  { tech: 'html', q: 'how to build a website', a: 'Start with an index.html for structure, add CSS for style and a little JavaScript for behaviour; I can hand you a full working template.' },
  { tech: 'html', q: 'hogyan csinaljak egy weboldalt', a: 'Egy index.html adja a szerkezetet, a CSS a stílust, a JavaScript a viselkedést; kérd, és adok egy teljes, működő sablont.' },
  { tech: 'html', q: 'what do i need to make a website', a: 'Just a text editor and a browser. One HTML file with inline CSS already works with no build step.' },
  { tech: 'html', q: 'how to make a landing page', a: 'A header with a nav, a hero with a title and button, feature cards in a grid, and a footer.' },
  { tech: 'css', q: 'how to make a website responsive', a: 'Use a flexible container, a wrapping grid, relative units, and media queries for phone, tablet and desktop.' },
  { tech: 'css', q: 'how to make a navbar', a: 'A flex row with the logo on the left and a list of links on the right; hide the list on small screens.' },
  { tech: 'html', q: 'how to add a button', a: 'Use a button element, or style an anchor as a button with padding, a background colour and a border radius.' },
  { tech: 'javascript', q: 'how to handle a click', a: 'Select the element and call addEventListener with the click event and a handler function.' },
  { tech: 'react', q: 'how to build a react app', a: 'Create it with Vite, write components that return JSX, keep data in useState, and run npm run dev.' },
  { tech: 'node', q: 'how to make a web server', a: 'Use the Node http module: createServer with a handler, then listen on a port like 3000.' },
  { tech: 'node', q: 'how to deploy a website', a: 'Static pages go to GitHub Pages, Netlify or Vercel; a Node server runs on a cloud instance or platform.' },
  { tech: 'html', q: 'how to make a form', a: 'Use a form with input and textarea fields, labels, the required attribute, and a submit button.' },
  { tech: 'css', q: 'how to use grid in css', a: 'Set display:grid and grid-template-columns; fr units share the space between columns.' },
  { tech: 'css', q: 'how to use flexbox', a: 'display:flex, then justify-content along the main axis and align-items across it, with gap for spacing.' },
  { tech: 'html', q: 'how to make a blog', a: 'List each post as an article card with a title, date and excerpt, with a sidebar for links.' },
  { tech: 'css', q: 'how to make an image gallery', a: 'Use a CSS grid with repeat auto-fill and minmax so the photos reflow to fit the screen.' },
  { tech: 'css', q: 'how to make a pricing page', a: 'Lay three plan cards in a flex row and highlight the middle one as popular.' },
  { tech: 'css', q: 'how to make a dashboard', a: 'Use a grid app shell: a fixed sidebar, a top bar, and a main area of stat cards.' },
  { tech: 'javascript', q: 'how to make a todo app', a: 'Keep an array of items, render them as a list, toggle done and delete, and save to localStorage.' },
  { tech: 'javascript', q: 'how to save data in the browser', a: 'Use localStorage.setItem with JSON.stringify, and read it back with JSON.parse.' },
  // language-specific coding tasks (programmer-oriented)
  { tech: 'python', q: 'how to read a file in python', a: "Open it in a with block: with open('file.txt') as f: text = f.read()." },
  { tech: 'python', q: 'how to make a http request in python', a: 'Use the requests library: r = requests.get(url); data = r.json().' },
  { tech: 'python', q: 'how to define a function in python', a: 'Use def: def add(a, b): return a + b.' },
  { tech: 'python', q: 'how to loop in python', a: 'Use a for loop: for item in items: print(item).' },
  { tech: 'kotlin', q: 'what is a data class in kotlin', a: 'A class that auto-generates equals, hashCode, toString and copy from its properties: data class User(val name: String).' },
  { tech: 'php', q: 'how to connect to mysql in php', a: 'Use PDO: new PDO("mysql:host=localhost;dbname=app", user, pass).' },
  { tech: 'sql', q: 'how to select data in sql', a: 'SELECT columns FROM table WHERE condition ORDER BY column.' },
  { tech: 'sql', q: 'how to join tables in sql', a: 'SELECT ... FROM a JOIN b ON b.id = a.b_id.' },
  { tech: 'java', q: 'how to write a for loop in java', a: 'for (int i = 0; i < n; i++) { ... }.' },
  ...LANG_QA,
  ...DESIGN_QA,
];

// Keyword set for "is this a programming question?" coverage in the arbiter.
export const PROG_KEYWORDS = new Set<string>(
  (
    'javascript js node react hook useeffect usestate component jsx html css flexbox flex grid div center ' +
    'tailwind bootstrap java class method jvm main native mobile fetch promise async array function props ' +
    'python py kotlin php phpmyadmin oracle vite mysql mariadb sql sqlt query database table select join insert ' +
    'express django flask spring laravel api server endpoint route json npm pip gradle maven import export ' +
    'loop for while if else variable const let def return file read write request response error debug compile ' +
    'fuggveny komponens valtozo ciklus kozepre allapot adatbazis lekerdezes szerver fajl kod programozas ' +
    LANG_KEYWORDS +
    ' ' +
    DESIGN_KEYWORDS
  ).split(/\s+/),
);

/** Is this query a programming/coding question? (tech name or coding keyword present) */
export function isProgrammingQuery(query: string): boolean {
  const words = normalizeTechQuery(query).match(/[a-z0-9]{2,}/g) ?? [];
  for (const w of words) if (PROG_KEYWORDS.has(w)) return true;
  return false;
}

// Title words per snippet, normalized once ("C#" → csharp, "C++" → cpp, ".NET" → dotnet).
// Glue words never count — "fish and chips in town" must not hit "Variables and types in …".
const TITLE_STOP = new Set('in and or the with to of on an from is by as at its'.split(' '));
const titleWordCache = new Map<ProgSnippet, string[]>();
function titleWords(s: ProgSnippet): string[] {
  let w = titleWordCache.get(s);
  if (!w) {
    w = [...new Set(normalizeTechQuery(s.title).match(/[a-z0-9]{2,}/g) ?? [])].filter((x) => !TITLE_STOP.has(x));
    titleWordCache.set(s, w);
  }
  return w;
}

/** Best matching snippet for a CODE/how-to question. Requires real title-word overlap
 *  (not just the tech name), so conceptual "what is X" falls through to the prose
 *  knowledge answer, while "how to read a file in python" returns code. A title word
 *  of 4+ letters also matches an inflected form ("python" → "pythonban"), and the
 *  optional `alt` stems match Hungarian wording ("ciklus" → "ciklust"). An optional
 *  `accept` filter skips candidates that don't answer the question. */
export function findSnippet(query: string, accept?: (s: ProgSnippet) => boolean): ProgSnippet | null {
  const q = normalizeTechQuery(query);
  const qWords = q.match(/[a-z0-9]{2,}/g) ?? [];
  const words = new Set<string>(qWords);
  const hasPrefix = (stem: string) => qWords.some((w) => w.startsWith(stem));
  let best: ProgSnippet | null = null;
  let bestScore = 0;
  for (const s of PROGRAMMING_SNIPPETS) {
    let score = mentionsTech(q, s.tech) ? 1 : 0;
    for (const w of titleWords(s)) if (words.has(w) || (w.length >= 4 && hasPrefix(w))) score += 2;
    for (const a of s.alt ?? []) if (hasPrefix(a)) score += 2;
    // `accept` (the relevance gate) lets the best snippet that REALLY answers win
    if (score >= 4 && score > bestScore && (!accept || accept(s))) {
      bestScore = score;
      best = s;
    }
  }
  return bestScore >= 4 ? best : null; // ≥ 2 meaningful title-word matches
}
