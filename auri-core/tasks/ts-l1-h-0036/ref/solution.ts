// AURI-CANARY-1faa60ea-36b9-5973-b1a8-ccca50194756
// Reference solution: only for validating the task.
export function szoMinta(minta: string, s: string): boolean {
  const w = s.split(/\s+/).filter(Boolean);
  const p = [...minta];
  if (w.length !== p.length) return false;
  const pairs = new Set(p.map((c, i) => c + '\u0000' + w[i]));
  return new Set(p).size === new Set(w).size && pairs.size === new Set(w).size;
}
