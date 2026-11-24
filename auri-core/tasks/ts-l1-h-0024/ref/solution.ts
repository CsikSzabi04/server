// AURI-CANARY-9cfed738-9ee5-5b19-b178-f85b6aa4cf92
// Reference solution: only for validating the task.
export function honapNapjai(ev: number, ho: number): number {
  if (!(ho >= 1 && ho <= 12)) throw new RangeError(String(ho));
  if (ho === 2) return ev % 4 === 0 && (ev % 100 !== 0 || ev % 400 === 0) ? 29 : 28;
  return [4, 6, 9, 11].includes(ho) ? 30 : 31;
}
