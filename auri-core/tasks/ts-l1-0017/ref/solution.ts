// AURI-CANARY-71415bf7-1b3e-58ac-835b-263d42d7d00d
// Reference solution: only for validating the task.
export function hosszSzerint(szavak: string[]): Record<number, string[]> {
  const d: Record<number, string[]> = {};
  for (const w of szavak) (d[[...w].length] ??= []).push(w);
  return d;
}
