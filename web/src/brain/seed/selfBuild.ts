// selfBuild.ts — the brain "builds itself": it keeps generating CONNECTABLE concept
// knowledge in the background. Two visible kinds (the user wants BOTH on /brain):
//   • CONNECTED clusters — a known hub (react, node, python, sql, science…) linked to
//     several related concepts → the new knowledge attaches to what already exists.
//   • ISOLATED concepts — standalone "knowledge balls" not wired to anything yet.
// Plus a large stream of count==1 data tokens for sheer vocabulary size.
// All tagged source 'bulk:self' → NOT persisted (regenerated each session, fast saves).

// Existing anchors already in the brain — clusters start here so new knowledge
// CONNECTS to the existing graph (the user: "összekapcsolható a már meglévőkkel").
const HUBS = [
  'react', 'node', 'python', 'java', 'kotlin', 'php', 'sql', 'mysql', 'oracle', 'vite', 'css', 'html', 'javascript',
  'typescript', 'docker', 'git', 'api', 'database', 'linux', 'android', 'spring', 'django', 'flask', 'express',
  'tailwind', 'bootstrap', 'graphql', 'redis', 'mongo', 'webpack',
  // devops / mobile / ai / networking / security domains
  'kubernetes', 'cicd', 'android', 'ios', 'flutter', 'swift', 'machinelearning', 'ai', 'http', 'dns', 'rest',
  'network', 'devops', 'mobile', 'cloud', 'json', 'regex', 'encryption', 'auth',
  // general-knowledge hubs too, so it is not only programming
  'science', 'history', 'geography', 'biology', 'physics', 'chemistry', 'mathematics', 'music', 'art', 'economy',
  'language', 'space', 'nature', 'health', 'energy', 'computer', 'internet', 'data', 'design', 'security',
];

// Real concept words that attach to the hubs (programming + general).
const CONCEPTS = [
  'module', 'package', 'function', 'variable', 'loop', 'array', 'object', 'class', 'method', 'interface', 'async',
  'promise', 'callback', 'event', 'handler', 'router', 'middleware', 'controller', 'service', 'repository', 'entity',
  'schema', 'migration', 'query', 'index', 'cache', 'session', 'token', 'cookie', 'header', 'request', 'response',
  'endpoint', 'json', 'config', 'environment', 'deployment', 'container', 'image', 'volume', 'network', 'port',
  'socket', 'thread', 'process', 'memory', 'algorithm', 'recursion', 'iteration', 'pointer', 'reference', 'closure',
  'scope', 'prototype', 'inheritance', 'polymorphism', 'encapsulation', 'abstraction', 'generic', 'enum', 'tuple',
  'set', 'map', 'queue', 'stack', 'tree', 'graph', 'hash', 'sort', 'search', 'binary', 'heap', 'matrix', 'vector',
  'tensor', 'model', 'dataset', 'feature', 'label', 'training', 'inference', 'neuron', 'layer', 'weight', 'gradient',
  'epoch', 'batch', 'optimizer', 'loss', 'pipeline', 'workflow', 'branch', 'merge', 'commit', 'release', 'version',
  'test', 'mock', 'fixture', 'coverage', 'debug', 'profile', 'benchmark', 'logging', 'metric', 'alert', 'cluster',
  // general
  'theory', 'experiment', 'evidence', 'hypothesis', 'energy', 'matter', 'force', 'motion', 'gravity', 'atom',
  'molecule', 'cell', 'gene', 'protein', 'evolution', 'ecosystem', 'climate', 'planet', 'galaxy', 'star', 'orbit',
  'market', 'trade', 'currency', 'inflation', 'culture', 'grammar', 'literature', 'rhythm', 'harmony', 'pigment',
  'philosophy', 'psychology', 'society', 'history', 'empire', 'revolution', 'continent', 'ocean', 'mountain',
  'river', 'desert', 'forest', 'organ', 'muscle', 'nerve', 'vitamin', 'nutrient', 'reaction', 'element', 'compound',
  // more programming + general concepts (so the visible brain fills densely)
  'component', 'hook', 'state', 'props', 'context', 'reducer', 'selector', 'directive', 'decorator', 'annotation',
  'closure', 'iterator', 'generator', 'stream', 'buffer', 'channel', 'mutex', 'semaphore', 'lock', 'atomic',
  'cache', 'proxy', 'gateway', 'loadbalancer', 'cluster', 'replica', 'shard', 'partition', 'backup', 'restore',
  'token', 'session', 'cookie', 'header', 'payload', 'schema', 'migration', 'seed', 'fixture', 'snapshot',
  'render', 'layout', 'style', 'animation', 'transition', 'gesture', 'viewport', 'breakpoint', 'palette', 'theme',
  'kernel', 'driver', 'process', 'syscall', 'register', 'cache2', 'pipeline', 'compiler', 'linker', 'assembler',
  'planet', 'comet', 'asteroid', 'nebula', 'photon', 'electron', 'proton', 'neutron', 'isotope', 'enzyme',
  'hormone', 'membrane', 'chromosome', 'mitochondria', 'synapse', 'cortex', 'reflex', 'immunity', 'antibody',
  'climate', 'weather', 'erosion', 'volcano', 'earthquake', 'tectonic', 'glacier', 'biome', 'habitat', 'species',
  'market', 'supply', 'demand', 'inflation', 'interest', 'investment', 'budget', 'revenue', 'profit', 'tax',
];

const CLUSTER = 5; // hub + 4 related per connected cluster

/** Connected clusters: [hub, hub_concept, hub_concept, …] → new knowledge wired to a hub. */
export function* selfBuildConnected(limit: number): Generator<string[]> {
  let n = 0;
  for (const hub of HUBS) {
    for (let i = 0; i < CONCEPTS.length; i += CLUSTER - 1) {
      const cluster = [hub, ...CONCEPTS.slice(i, i + CLUSTER - 1).map((c) => `${hub}_${c}`)];
      if (cluster.length < 2) continue;
      yield cluster;
      n += cluster.length;
      if (n >= limit) return;
    }
  }
}

/** Isolated concepts: standalone "knowledge balls", not connected to anything. */
export function* selfBuildIsolated(limit: number): Generator<string> {
  let n = 0;
  for (const c of CONCEPTS) {
    for (const hub of HUBS) {
      yield `${c}_${hub}`; // distinct standalone concept token
      if (++n >= limit) return;
    }
  }
}

/** Large count==1 data stream (sheer vocabulary), connectable phrasing. */
export function* selfBuildData(limit: number): Generator<string[]> {
  let n = 0;
  let cur: string[] = [];
  for (const hub of HUBS) {
    for (const a of CONCEPTS) {
      for (const b of CONCEPTS) {
        cur.push(`${hub}${a}${b}`);
        if (cur.length >= 6) {
          yield cur;
          n += cur.length;
          cur = [];
          if (n >= limit) return;
        }
      }
    }
  }
  if (cur.length) yield cur;
}
