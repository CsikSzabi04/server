// AURI-CANARY-344656a8-e848-5362-9093-dbe2051c20ed
// Reference solution: only for validating the task.
export function kozosElotag(szavak: string[]): string {
  if (!szavak.length) return '';
  let p = szavak[0];
  for (const w of szavak.slice(1)) while (!w.startsWith(p)) p = p.slice(0, -1);
  return p;
}
