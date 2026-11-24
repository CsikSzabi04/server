// AURI-CANARY-48579f0a-bc56-5c2a-9fc9-bb2b2f474776
// Reference solution: only for validating the task.
export function leghosszabbSzo(s: string): string {
  let best = '';
  for (const w of s.split(/\s+/)) if (w.length > best.length) best = w;
  return best;
}
