// AURI-CANARY-67e8e2a7-1ee2-5727-90c1-7155075cc44b
// Reference solution: only for validating the task.
export function idoFormatum(mp: number): string {
  if (!(mp >= 0 && mp < 86400)) throw new RangeError(String(mp));
  const p = (x: number) => String(x).padStart(2, '0');
  return `${p(Math.floor(mp / 3600))}:${p(Math.floor(mp / 60) % 60)}:${p(mp % 60)}`;
}
