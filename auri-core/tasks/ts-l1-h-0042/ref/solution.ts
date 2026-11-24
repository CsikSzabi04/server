// AURI-CANARY-d436fa57-5dbf-5f5a-b73e-0d63642c9758
// Reference solution: only for validating the task.
export function modusz(xs: number[]): number | null {
  if (!xs.length) return null;
  const c = new Map<number, number>();
  for (const x of xs) c.set(x, (c.get(x) ?? 0) + 1);
  let best = xs[0];
  for (const [x, k] of c) if (k > c.get(best)! || (k === c.get(best) && x < best)) best = x;
  return best;
}
