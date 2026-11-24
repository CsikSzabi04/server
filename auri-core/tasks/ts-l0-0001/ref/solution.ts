// AURI-CANARY-f33d6555-8c44-5dd8-bdec-12b36b23816b
// Reference solution: only for validating the task.
export function parosSzamok(xs: number[]): number[] {
  return xs.filter((x) => x % 2 === 0);
}
