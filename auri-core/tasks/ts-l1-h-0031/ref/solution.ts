// AURI-CANARY-ab9d945c-9611-573a-a611-19477961c997
// Reference solution: only for validating the task.
export function matrixForgat(m: number[][]): number[][] {
  if (m.some((r) => r.length !== m[0].length)) throw new RangeError('nem téglalap');
  return m.length ? m[0].map((_, j) => m.map((r) => r[j]).reverse()) : [];
}
