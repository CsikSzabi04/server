// AURI-CANARY-36faccdf-7890-55d9-9ce0-b99958b109e2
// Reference solution: only for validating the task.
export function pascalSor(n: number): number[] {
  if (n < 0) throw new RangeError(String(n));
  let row = [1];
  for (let i = 0; i < n; i++) row = [0, ...row].map((a, j) => a + (row[j] ?? 0));
  return row;
}
