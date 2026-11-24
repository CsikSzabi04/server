// AURI-CANARY-2857cad5-f249-515f-a19d-0a228abb7a10
// Reference solution: only for validating the task.
export function elsoEgyedi(s: string): string | null {
  const c = new Map<string, number>();
  for (const ch of s) c.set(ch, (c.get(ch) ?? 0) + 1);
  for (const ch of s) if (c.get(ch) === 1) return ch;
  return null;
}
