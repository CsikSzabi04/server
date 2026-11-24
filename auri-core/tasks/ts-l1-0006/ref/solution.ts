// AURI-CANARY-6c95c76a-3702-5ecb-8c1e-b8c7f53c286d
// Reference solution: only for validating the task.
export function rleKodol(s: string): string {
  let out = '';
  const cs = [...s];
  for (let i = 0; i < cs.length; ) {
    let j = i;
    while (j < cs.length && cs[j] === cs[i]) j++;
    out += `${j - i}${cs[i]}`;
    i = j;
  }
  return out;
}
