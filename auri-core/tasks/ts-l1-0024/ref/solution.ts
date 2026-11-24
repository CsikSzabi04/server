// AURI-CANARY-fd70fa72-93ae-5573-92d2-7a9f66cdea22
// Reference solution: only for validating the task.
export function sortores(szoveg: string, szelesseg: number): string[] {
  if (szelesseg < 1) throw new RangeError(String(szelesseg));
  const sorok: string[] = [];
  let cur = '';
  for (const w of szoveg.split(/\s+/).filter(Boolean)) {
    if (cur && cur.length + 1 + w.length <= szelesseg) cur += ` ${w}`;
    else {
      if (cur) sorok.push(cur);
      cur = w;
    }
  }
  if (cur) sorok.push(cur);
  return sorok;
}
