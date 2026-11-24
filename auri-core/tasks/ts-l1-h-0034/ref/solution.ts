// AURI-CANARY-587ca5d0-0f80-5dcb-b34a-8f69da65c135
// Reference solution: only for validating the task.
export function hamming(a: string, b: string): number {
  if (a.length !== b.length) throw new RangeError('eltérő hossz');
  return [...a].filter((c, i) => c !== b[i]).length;
}
