// AURI-CANARY-9a5bb87e-fcb4-547e-b1ef-c630df26e604
// Reference solution: only for validating the task.
export function snakeCamel(s: string): string {
  const p = s.split('_').filter(Boolean);
  if (!p.length) return '';
  return p[0].toLowerCase() + p.slice(1).map((x) => x[0].toUpperCase() + x.slice(1).toLowerCase()).join('');
}
