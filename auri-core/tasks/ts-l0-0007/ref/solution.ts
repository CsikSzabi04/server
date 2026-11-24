// AURI-CANARY-f82cb7bb-b396-5fab-a0e0-5bea17ce6b70
// Reference solution: only for validating the task.
export function celsiusFahrenheit(c: number): number {
  return Math.round((c * 9 / 5 + 32) * 10) / 10;
}
