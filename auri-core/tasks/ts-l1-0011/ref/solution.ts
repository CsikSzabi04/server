// AURI-CANARY-ff4d6d19-f32f-5de8-8669-32b8e51c8004
// Reference solution: only for validating the task.
export function statisztika(s: string): { betu: number; szamjegy: number; szokoz: number; egyeb: number } {
  const d = { betu: 0, szamjegy: 0, szokoz: 0, egyeb: 0 };
  for (const c of s) {
    if (/\p{L}/u.test(c)) d.betu++;
    else if (/\p{Nd}/u.test(c)) d.szamjegy++;
    else if (/\s/.test(c)) d.szokoz++;
    else d.egyeb++;
  }
  return d;
}
