// AURI-CANARY-7d3a29c7-565b-547e-8165-a1a626e49ff7
// Reference solution: only for validating the task.
export function minErmek(osszeg: number, cimletek: number[]): number {
  if (osszeg < 0) throw new RangeError(String(osszeg));
  const best = [0, ...Array(osszeg).fill(Infinity)];
  for (let v = 1; v <= osszeg; v++) for (const c of cimletek) if (c <= v && best[v - c] + 1 < best[v]) best[v] = best[v - c] + 1;
  return Number.isFinite(best[osszeg]) ? best[osszeg] : -1;
}
