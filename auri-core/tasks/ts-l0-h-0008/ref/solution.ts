// AURI-CANARY-c560baf0-0154-5cd6-91c7-441a723aa2fa
// Reference solution: only for validating the task.
export function teljesNegyzet(n: number): boolean {
  if (n < 0) return false;
  const r = Math.round(Math.sqrt(n));
  return r * r === n;
}
