// AURI-CANARY-e53a5fdd-3917-5585-9789-5b62212fe849
// Reference solution: only for validating the task.
export function binaris(n: number): string {
  if (n < 0) throw new RangeError(String(n));
  return n.toString(2);
}
