// AURI-CANARY-4eee5193-3586-585c-a7b8-4f796a05db35
// Reference solution: only for validating the task.
export function szokoev(ev: number): boolean {
  return ev % 4 === 0 && (ev % 100 !== 0 || ev % 400 === 0);
}
