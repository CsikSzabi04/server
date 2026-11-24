// AURI-CANARY-7ab287f2-ada5-50d5-8889-9fe53e377e5f
// Reference solution: only for validating the task.
export function nagybetusSzavak(s: string): string[] {
  return s.split(/\s+/).filter((w) => w !== '' && w[0] !== w[0].toLowerCase());
}
