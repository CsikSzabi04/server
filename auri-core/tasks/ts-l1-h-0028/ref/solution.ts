// AURI-CANARY-f2691306-b151-5e76-8b30-ea8b701e81d7
// Reference solution: only for validating the task.
export function racsUt(racs: string[]): number {
  if (!racs.length || !racs[0].length) return -1;
  const h = racs.length;
  const w = racs[0].length;
  if (racs[0][0] === '#' || racs[h - 1][w - 1] === '#') return -1;
  const dist = new Map<number, number>([[0, 0]]);
  const q = [0];
  for (let qi = 0; qi < q.length; qi++) {
    const r = Math.floor(q[qi] / w);
    const c = q[qi] % w;
    const d = dist.get(q[qi])!;
    if (r === h - 1 && c === w - 1) return d;
    for (const [nr, nc] of [[r + 1, c], [r - 1, c], [r, c + 1], [r, c - 1]]) {
      const k = nr * w + nc;
      if (nr >= 0 && nr < h && nc >= 0 && nc < w && racs[nr][nc] === '.' && !dist.has(k)) {
        dist.set(k, d + 1);
        q.push(k);
      }
    }
  }
  return -1;
}
