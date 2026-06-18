import type { BrainGraph } from './types';

// Lightweight 2D fallback for devices without WebGL (or when 3D is disabled).
// Shows the same data — regions with their concepts — as plain, readable chips.
export default function BrainFallback2D({ graph }: { graph: BrainGraph }) {
  return (
    <div className="brainx-fallback">
      <div className="brainx-fallback-note">3D unavailable on this device — showing the memory map in 2D.</div>
      {graph.regions.map((r) => {
        const nodes = graph.nodes.filter((n) => n.regionId === r.id);
        if (nodes.length === 0) return null;
        return (
          <section key={r.id} className="brainx-fb-region">
            <h3 style={{ color: `hsl(${r.hue}, 90%, 62%)` }}>{r.label}</h3>
            <div className="brainx-fb-chips">
              {nodes
                .slice()
                .sort((a, b) => b.weight - a.weight)
                .map((n) => (
                  <span
                    key={n.id}
                    className="brainx-fb-chip"
                    style={{ borderColor: n.color, color: n.color }}
                    title={`${n.kind} · w${n.weight}`}
                  >
                    {n.pinned ? '★ ' : ''}
                    {n.label}
                  </span>
                ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
