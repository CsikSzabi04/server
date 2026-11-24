// AURI-CANARY-f99ed2b4-482e-59a4-bc21-2210393a8a4d
// Reference solution: only for validating the task.
export function kezdobetuk(s: string): string {
  return s.split(/\s+/).filter(Boolean).map((w) => w[0].toUpperCase()).join('');
}
