// AURI-CANARY-f077ffbc-0ac3-5102-9aef-2a5b4adefa5b
// Reference solution: only for validating the task.
export function maganhangzok(s: string): number {
  return [...s.toLowerCase()].filter((c) => 'aáeéiíoóöőuúüű'.includes(c)).length;
}
