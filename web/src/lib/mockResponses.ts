// Canned "Auri" responses for MOCK mode (no backend). A deliberate mix of short
// and long answers so the length-proportional "stay alive longer" animation is
// visibly demonstrable. HUD-flavored, English.

const GREETINGS = [
  'System online. Auri on standby — how can I help?',
  'Link established. I am listening.',
  'Auri active. Give me the command.',
];

const SHORT = [
  'Copy that. Processing and reporting back.',
  'Done. Operation successful.',
  'Confirmed. Continuing to monitor.',
  'No anomalies. All systems within nominal parameters.',
];

const LONG = [
  `Analyzing the request. I process the incoming data stream in three layers: first I normalize the context, then I extract the relevant patterns, and finally I summarize the conclusion.

Based on the current telemetry, every subsystem is stable: the energy core pulses at nominal levels, the network uplink latency is negligible, and there are no fault signals on the peripherals. The longer my answer, the longer the display keeps shimmering — fresh text glows, then slowly settles into calm, as if the system itself were breathing.

If you like, I can run a deeper diagnostic, or connect you to the real backend — just set the API endpoint.`,

  `Affirmative. I'm accessing the requested module and will walk you through it step by step.

First I survey the environment and the available resources. Then I build the execution plan, ordering the steps by priority so the critical path comes first. Meanwhile I keep watching the feedback, and the moment I detect a deviation from expected behavior, I correct course.

This interface is currently running in demo (mock) mode, so you can see the full experience without a real language model: the spinning energy core, the sweeping scan lines, the text coming alive. As soon as you wire up the private Auri server, this same interface will stream real answers — token by token, as the model thinks.`,
];

// Code-bearing replies so the Code workspace (and its "Apply"/diff flow) is
// demoable without a backend. Each ends with a fenced block the UI can apply.
const CODE = [
  `Here's a small, reusable helper — apply it to the open file:

\`\`\`js
export async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(\`HTTP \${res.status} on \${url}\`);
  return res.json();
}
\`\`\`

Use the “Apply” button to drop it into the active file, or “Diff” to review first.`,
  `Done — I refactored it into a clean, typed function:

\`\`\`ts
type Point = { x: number; y: number };

export function distance(a: Point, b: Point): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}
\`\`\`

This is DEMO mode, so the snippet is canned. Wire up the real backend for live, context-aware code.`,
  `Sure. Here's a minimal component you can build on:

\`\`\`jsx
export default function Counter() {
  const [n, setN] = useState(0);
  return <button onClick={() => setN((v) => v + 1)}>Count: {n}</button>;
}
\`\`\`

Review the diff, then apply it to the file on the left.`,
];

let greetUsed = false;

export function pickMockReply(userText: string): string {
  const t = userText.toLowerCase().trim();

  if (!greetUsed && (t === '' || /\b(hi|hello|hey|yo|hiya|greetings|sup)\b/.test(t))) {
    greetUsed = true;
    return GREETINGS[Math.floor(Math.random() * GREETINGS.length)];
  }

  // Code intent -> reply with a fenced code block (drives the Code workspace).
  if (
    t.includes('```') ||
    /\b(code|kód|function|függvény|fetch|component|komponens|class|refactor|typescript|javascript|python|bug|fix|javíts|írj|write|add|implement)\b/.test(
      t,
    )
  ) {
    return CODE[Math.floor(Math.random() * CODE.length)];
  }

  // Longer questions -> longer answers (so the long-text animation shows up).
  if (t.length > 40 || /\b(why|how|explain|detail|plan|analyze|analyse)\b/.test(t)) {
    return LONG[Math.floor(Math.random() * LONG.length)];
  }

  return SHORT[Math.floor(Math.random() * SHORT.length)];
}
