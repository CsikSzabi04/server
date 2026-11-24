// AURI-CANARY-1a4500b2-6341-5371-b794-a2055a0e04bf
// Reference solution: only for validating the task.
export function mozgoAtlag(xs: number[], k: number): number[] {
  if (k < 1) throw new RangeError(String(k));
  const out: number[] = [];
  for (let i = 0; i + k <= xs.length; i++) out.push(Math.round((xs.slice(i, i + k).reduce((a, b) => a + b, 0) / k) * 100) / 100);
  return out;
}
