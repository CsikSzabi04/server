// AURI-CANARY-f702c693-55a9-53bd-95ac-5440e3a3579e
// Reference solution: only for validating the task.
export function lepcso(n: number): number {
  if (n < 0) throw new RangeError(String(n));
  let a = 1;
  let b = 1;
  for (let i = 0; i < n; i++) [a, b] = [b, a + b];
  return a;
}
