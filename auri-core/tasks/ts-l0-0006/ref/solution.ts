// AURI-CANARY-abea2614-d391-500c-88f6-c7e6214cd603
// Reference solution: only for validating the task.
export function szavakSzama(s: string): number {
  return s.split(/\s+/).filter(Boolean).length;
}
