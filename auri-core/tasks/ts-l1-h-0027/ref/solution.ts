// AURI-CANARY-770b51a3-b3a1-5270-bd9f-4dbc204c81fb
// Reference solution: only for validating the task.
export function ezresTagolas(n: number): string {
  const d = String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return n < 0 ? '-' + d : d;
}
