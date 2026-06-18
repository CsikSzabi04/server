// AI-2 uses the SHARED contracts (AI-1 owns web/src/brain/contracts.ts).
// We re-export them so the rest of brain-view imports from one local path.
import type { BrainNode } from '../brain/contracts';

export type {
  BrainNode,
  BrainNodeKind,
  BrainEdge,
  BrainRegion,
  BrainGraph,
  BrainStats,
  BrainState,
  BrainStage,
} from '../brain/contracts';

/** 3D layout positions, keyed by node id. */
export type Positions = Record<string, [number, number, number]>;

/** Knowledge the brain learned from the web (region:web, or a node whose source
 *  is a URL). Used by the 3D view to color it distinctly + flash it on arrival,
 *  ahead of AI-1/AI-3 wiring the web-search askPipeline. Forward-compatible:
 *  matches nothing until those web nodes exist, so it's harmless today. */
export function isWebNode(n: BrainNode): boolean {
  return n.regionId === 'region:web' || /^https?:\/\//i.test(n.sources?.[0] ?? '');
}
