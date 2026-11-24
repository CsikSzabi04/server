// AURI-CANARY-4bf3ed7f-410b-5d7c-bf25-c920496aeacd
// Reference solution: only for validating the task.
export function atlag(xs: number[]): number | null {
  return xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 100) / 100 : null;
}
