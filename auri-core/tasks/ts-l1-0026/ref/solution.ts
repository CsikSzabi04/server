// AURI-CANARY-a4d9683d-9188-5f7a-8ba3-fc3218621614
// Reference solution: only for validating the task.
export function telefonszam(s: string): string {
  const m = /^(?:\+36|36|06)(\d{9})$/.exec(s.replace(/[ \-/()]/g, ''));
  if (!m) throw new RangeError(s);
  return `+36${m[1]}`;
}
