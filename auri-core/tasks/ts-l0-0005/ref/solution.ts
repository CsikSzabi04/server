// AURI-CANARY-a605c37e-b060-5b86-9596-9ab6e7c933e8
// Reference solution: only for validating the task.
export function szamjegyosszeg(n: number): number {
  return [...String(Math.abs(n))].reduce((a, d) => a + Number(d), 0);
}
