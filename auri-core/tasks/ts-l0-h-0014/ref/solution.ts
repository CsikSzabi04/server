// AURI-CANARY-ed166b2d-0914-57e4-8ed9-27ee7aa313c4
// Reference solution: only for validating the task.
export function atlagonFeluli(xs: number[]): number[] {
  const s = xs.reduce((a, b) => a + b, 0);
  return xs.filter((x) => x * xs.length > s);
}
