// AURI-CANARY-05fc9fbd-09e4-57e4-be0a-0afad7f4df7f
// Reference solution: only for validating the task.
export function szigetek(terkep: string[]): number {
  const h = terkep.length;
  const w = h ? terkep[0].length : 0;
  const seen = new Set<number>();
  let db = 0;
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      if (terkep[r][c] !== '#' || seen.has(r * w + c)) continue;
      db++;
      seen.add(r * w + c);
      const stack = [[r, c]];
      while (stack.length) {
        const [y, x] = stack.pop()!;
        for (const [ny, nx] of [[y + 1, x], [y - 1, x], [y, x + 1], [y, x - 1]]) {
          if (ny >= 0 && ny < h && nx >= 0 && nx < w && terkep[ny][nx] === '#' && !seen.has(ny * w + nx)) {
            seen.add(ny * w + nx);
            stack.push([ny, nx]);
          }
        }
      }
    }
  }
  return db;
}
