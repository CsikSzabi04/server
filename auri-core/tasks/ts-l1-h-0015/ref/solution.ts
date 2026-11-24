// AURI-CANARY-a9d8fb02-1aa0-5a67-850a-ee58abdfad10
// Reference solution: only for validating the task.
export function tokeletes(n: number): boolean {
  if (n < 2) return false;
  let s = 1;
  for (let i = 2; i * i <= n; i++) if (n % i === 0) s += i * i === n ? i : i + n / i;
  return s === n;
}
