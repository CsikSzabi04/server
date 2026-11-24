// AURI-CANARY-9ced5d8f-9918-53d2-85ee-dfbe980180a2
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { forgat } from '../solution.ts';

const f = forgat as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `forgat(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[], 3], []], [[[1, 2, 3], 0], [1, 2, 3]], [[[1, 2, 3], 4], [3, 1, 2]], [[[1, 2, 3], -1], [2, 3, 1]], [[[1], 100], [1]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
test('forgat nem módosítja a bemenetet', () => {
  const xs = [1, 2, 3];
  forgat(xs, 1);
  assert.deepEqual(xs, [1, 2, 3], 'forgat(xs, 1) után az xs változatlan');
});
