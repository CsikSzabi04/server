// AURI-CANARY-718c62d1-65c1-50a8-a62f-4d5ff1696d06
// Reference solution: only for validating the task.
export function ipv4Ervenyes(s: string): boolean {
  const p = s.split('.');
  return p.length === 4 && p.every((x) => /^(0|[1-9][0-9]{0,2})$/.test(x) && Number(x) <= 255);
}
