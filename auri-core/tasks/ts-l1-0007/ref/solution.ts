// AURI-CANARY-cd986c0a-d877-5dd0-88f5-117e7a1128b6
// Reference solution: only for validating the task.
export function rleDekodol(s: string): string {
  const parts = [...s.matchAll(/(\d+)(\D)/gu)];
  if (parts.map((m) => m[0]).join('') !== s || parts.some((m) => Number(m[1]) === 0)) throw new RangeError(s);
  return parts.map((m) => m[2].repeat(Number(m[1]))).join('');
}
