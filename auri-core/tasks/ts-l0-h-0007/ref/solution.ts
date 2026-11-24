// AURI-CANARY-5b72fbd1-5ccf-5d62-86fd-db5b5093bff4
// Reference solution: only for validating the task.
export function haromszog(a: number, b: number, c: number): boolean {
  return Math.min(a, b, c) > 0 && a + b > c && a + c > b && b + c > a;
}
