// AURI-CANARY-23919316-df3f-540d-a8a5-ca3acdcd5244
// Reference solution: only for validating the task.
export function kozos(a: number[], b: number[]): number[] {
  const bs = new Set(b);
  return [...new Set(a)].filter((x) => bs.has(x));
}
