// AURI-CANARY-88f3633a-699d-5964-8183-cd0951d9f7ea
// Reference solution: only for validating the task.
export function permutaciok(s: string): string[] {
  const out = new Set<string>();
  const go = (rest: string, acc: string): void => {
    if (!rest) {
      out.add(acc);
      return;
    }
    for (let i = 0; i < rest.length; i++) go(rest.slice(0, i) + rest.slice(i + 1), acc + rest[i]);
  };
  go(s, '');
  return [...out].sort();
}
