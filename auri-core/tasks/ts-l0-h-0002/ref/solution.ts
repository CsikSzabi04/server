// AURI-CANARY-692ac689-7541-5642-9ef9-b195e913a2b3
// Reference solution: only for validating the task.
export function faktorialis(n: number): number {
  if (n < 0) throw new RangeError(String(n));
  let r = 1;
  for (let i = 2; i <= n; i++) r *= i;
  return r;
}
