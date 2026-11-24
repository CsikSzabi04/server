// AURI-CANARY-d592ed01-d36c-57d2-8913-36317cd95aff
// Reference solution: only for validating the task.
export function ketOsszeg(xs: number[], cel: number): number[] | null {
  const seen = new Map<number, number>();
  for (let j = 0; j < xs.length; j++) {
    const i = seen.get(cel - xs[j]);
    if (i !== undefined) return [i, j];
    if (!seen.has(xs[j])) seen.set(xs[j], j);
  }
  return null;
}
