// AURI-CANARY-0f4db97b-d067-546a-9695-8ae293bc3394
// Reference solution: only for validating the task.
export function negyzetosszeg(n: number): number {
  let s = 0;
  for (let i = 1; i <= n; i++) s += i * i;
  return s;
}
