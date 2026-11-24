// AURI-CANARY-2240b986-d569-5f06-afce-0a485e38bbb2
// Reference solution: only for validating the task.
export function vanIsmetlodes(xs: number[]): boolean {
  return new Set(xs).size < xs.length;
}
