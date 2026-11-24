// AURI-CANARY-21b52a1b-f037-5467-b5ef-fbbe23654e72
// Reference solution: only for validating the task.
export function ismetel(s: string, n: number, sep: string): string {
  return Array(Math.max(0, n)).fill(s).join(sep);
}
