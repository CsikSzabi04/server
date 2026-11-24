// AURI-CANARY-a5aac386-088d-5257-9b32-9be7ef00906b
// Reference solution: only for validating the task.
export function caesar(s: string, k: number): string {
  const sh = (c: string, base: number) => String.fromCharCode(((((c.charCodeAt(0) - base + k) % 26) + 26) % 26) + base);
  return [...s].map((c) => (c >= 'a' && c <= 'z' ? sh(c, 97) : c >= 'A' && c <= 'Z' ? sh(c, 65) : c)).join('');
}
