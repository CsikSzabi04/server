// AURI-CANARY-904ec899-da53-5876-b93c-95fd885a3a99
// Reference solution: only for validating the task.
export function huszar(mezo: string): string[] {
  if (!/^[a-h][1-8]$/.test(mezo)) throw new RangeError(mezo);
  const c = mezo.charCodeAt(0) - 97;
  const r = Number(mezo[1]);
  const out: string[] = [];
  for (const [dc, dr] of [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]) {
    if (c + dc >= 0 && c + dc < 8 && r + dr >= 1 && r + dr <= 8) out.push(String.fromCharCode(97 + c + dc) + (r + dr));
  }
  return out.sort();
}
