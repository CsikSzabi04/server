// AURI-CANARY-aa20550e-067d-57a4-9a66-1b0e798a618e
// Reference solution: only for validating the task.
export function transzponal(m: number[][]): number[][] {
  if (m.some((r) => r.length !== m[0].length)) throw new RangeError('nem téglalap');
  return m.length ? m[0].map((_, j) => m.map((r) => r[j])) : [];
}
