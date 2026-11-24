// AURI-CANARY-481f6c97-a709-5e95-8030-89c435a38c94
// Reference solution: only for validating the task.
export function pangramma(s: string): boolean {
  const t = s.toLowerCase();
  return [...'abcdefghijklmnopqrstuvwxyz'].every((c) => t.includes(c));
}
