// AURI-CANARY-b8387c55-c2d0-50f6-8730-8ee6c84893d2
// Reference solution: only for validating the task.
export function csvSor(s: string): string[] {
  const out: string[] = [];
  const n = s.length;
  let i = 0;
  for (;;) {
    if (s[i] === '"') {
      i++;
      let buf = '';
      for (;;) {
        if (i >= n) throw new RangeError('lezáratlan idézőjel');
        if (s[i] === '"') {
          if (s[i + 1] === '"') {
            buf += '"';
            i += 2;
            continue;
          }
          i++;
          break;
        }
        buf += s[i++];
      }
      if (i < n && s[i] !== ',') throw new RangeError('szöveg a záró idézőjel után');
      out.push(buf);
    } else {
      let j = s.indexOf(',', i);
      if (j < 0) j = n;
      const mezo = s.slice(i, j);
      if (mezo.includes('"')) throw new RangeError('idézőjel a mezőben');
      out.push(mezo);
      i = j;
    }
    if (i >= n) return out;
    i++;
  }
}
