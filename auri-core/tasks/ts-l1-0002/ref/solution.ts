// AURI-CANARY-3a555cbc-9406-50b1-9d6b-ba6a33020d9f
// Reference solution: only for validating the task.
export function romaiErtek(s: string): number {
  const V: Record<string, number> = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  const u = s.toUpperCase();
  if (!u || [...u].some((c) => !(c in V))) throw new RangeError(s);
  let total = 0;
  for (let i = 0; i < u.length; i++) {
    const v = V[u[i]];
    total += i + 1 < u.length && V[u[i + 1]] > v ? -v : v;
  }
  return total;
}
