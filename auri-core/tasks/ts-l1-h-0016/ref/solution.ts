// AURI-CANARY-2b0f25af-3993-593e-891d-6dd49a43d166
// Reference solution: only for validating the task.
export function collatzLepesek(n: number): number {
  if (n < 1) throw new RangeError(String(n));
  let k = 0;
  while (n !== 1) {
    n = n % 2 === 0 ? n / 2 : 3 * n + 1;
    k++;
  }
  return k;
}
