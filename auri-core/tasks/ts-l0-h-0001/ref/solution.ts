// AURI-CANARY-2d35d666-1f03-5f1c-bd71-5061d8eb1cdc
// Reference solution: only for validating the task.
export function paratlanOsszeg(xs: number[]): number {
  return xs.filter((x) => x % 2 !== 0).reduce((a, b) => a + b, 0);
}
