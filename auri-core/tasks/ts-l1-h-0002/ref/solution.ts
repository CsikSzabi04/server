// AURI-CANARY-0ec46c2b-8d70-5397-a506-bd218f60e6d6
// Reference solution: only for validating the task.
export function szamrendszer(n: number, b: number): string {
  if (n < 0 || b < 2 || b > 36) throw new RangeError(`${n} ${b}`);
  return n.toString(b);
}
