// AURI-CANARY-45e29d38-377a-57fe-8671-b9cf6d53d228
// Reference solution: only for validating the task.
export function matrixSzorzas(a: number[][], b: number[][]): number[][] {
  if (!a.length || !b.length || a[0].length !== b.length) throw new RangeError('méret');
  return a.map((r) => b[0].map((_, j) => r.reduce((s, x, k) => s + x * b[k][j], 0)));
}
