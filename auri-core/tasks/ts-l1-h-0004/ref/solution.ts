// AURI-CANARY-58219427-7a49-5c5c-bcff-c0c4afa9bdbc
// Reference solution: only for validating the task.
export function betuGyakorisag(s: string): Record<string, number> {
  const d: Record<string, number> = {};
  for (const c of s.toLowerCase()) if (/\p{L}/u.test(c)) d[c] = (d[c] ?? 0) + 1;
  return d;
}
