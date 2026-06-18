// sources.ts — curated, STATIC registry of official documentation links for the
// Programming region. Two uses: (1) input for the optional offline ingest script
// (AI-3 zone), (2) the runtime "cite the source" database the local brain uses to
// recommend an official link. No network here — just data.

export interface SourceLink {
  tech: string;
  title: string;
  url: string;
  topics: string[];
}

export const TECHS = [
  'node',
  'java',
  'javascript',
  'react',
  'html',
  'css',
  'tailwind',
  'bootstrap',
  'native',
] as const;
export type Tech = (typeof TECHS)[number];

export const TECH_LABEL: Record<Tech, string> = {
  node: 'Node.js',
  java: 'Java',
  javascript: 'JavaScript',
  react: 'React',
  html: 'HTML',
  css: 'CSS',
  tailwind: 'Tailwind CSS',
  bootstrap: 'Bootstrap',
  native: 'Native (mobile)',
};

export const SOURCES: SourceLink[] = [
  { tech: 'node', title: 'Node.js Documentation', url: 'https://nodejs.org/docs/latest/api/', topics: ['node', 'fs', 'http', 'module', 'npm', 'async', 'stream', 'buffer', 'process', 'server'] },
  { tech: 'javascript', title: 'MDN — JavaScript', url: 'https://developer.mozilla.org/en-US/docs/Web/JavaScript', topics: ['javascript', 'js', 'array', 'promise', 'async', 'await', 'function', 'object', 'closure', 'json', 'fetch'] },
  { tech: 'html', title: 'MDN — HTML', url: 'https://developer.mozilla.org/en-US/docs/Web/HTML', topics: ['html', 'element', 'tag', 'form', 'semantic', 'attribute', 'input', 'head', 'body', 'link'] },
  { tech: 'css', title: 'MDN — CSS', url: 'https://developer.mozilla.org/en-US/docs/Web/CSS', topics: ['css', 'flexbox', 'flex', 'grid', 'center', 'selector', 'box', 'margin', 'padding', 'responsive', 'media'] },
  { tech: 'react', title: 'React Documentation', url: 'https://react.dev/learn', topics: ['react', 'component', 'hook', 'useeffect', 'usestate', 'props', 'jsx', 'render', 'effect', 'state'] },
  { tech: 'java', title: 'Java SE Documentation', url: 'https://docs.oracle.com/en/java/javase/', topics: ['java', 'class', 'method', 'interface', 'jvm', 'main', 'static', 'object', 'exception', 'generics'] },
  { tech: 'tailwind', title: 'Tailwind CSS Documentation', url: 'https://tailwindcss.com/docs', topics: ['tailwind', 'utility', 'class', 'flex', 'grid', 'responsive', 'spacing', 'color', 'center'] },
  { tech: 'bootstrap', title: 'Bootstrap Documentation', url: 'https://getbootstrap.com/docs/', topics: ['bootstrap', 'grid', 'container', 'row', 'col', 'component', 'navbar', 'button', 'responsive'] },
  { tech: 'native', title: 'React Native Documentation', url: 'https://reactnative.dev/docs/getting-started', topics: ['native', 'reactnative', 'mobile', 'view', 'text', 'component', 'app'] },
  { tech: 'native', title: 'Android Developers', url: 'https://developer.android.com/docs', topics: ['android', 'native', 'mobile', 'activity', 'kotlin'] },
  { tech: 'native', title: 'Apple Developer Documentation', url: 'https://developer.apple.com/documentation/', topics: ['ios', 'native', 'mobile', 'swift', 'apple'] },
];

/** Best official source for a question (by tech name + topic-keyword overlap). */
export function findSource(query: string): SourceLink | null {
  const q = query.toLowerCase();
  const words: string[] = q.match(/[a-z0-9]{2,}/g) ?? [];
  let best: SourceLink | null = null;
  let bestScore = 0;
  for (const s of SOURCES) {
    let score = q.includes(s.tech) ? 3 : 0;
    for (const t of s.topics) if (words.includes(t)) score += 2;
    if (score > bestScore) {
      bestScore = score;
      best = s;
    }
  }
  return bestScore > 0 ? best : null;
}
