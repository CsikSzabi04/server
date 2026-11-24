// AURI-CANARY-f511e1f8-43cc-58b4-87b8-951d776e3409
// Reference solution: only for validating the task.
export function terjedelem(xs: number[]): number {
  return xs.length ? Math.max(...xs) - Math.min(...xs) : 0;
}
