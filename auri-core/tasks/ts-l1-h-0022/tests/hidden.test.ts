// AURI-CANARY-fabad109-3944-58ec-8b68-81fb01b9a32f
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kombinacio } from '../solution.ts';

const f = kombinacio as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kombinacio(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0, 0], 1], [[10, 0], 1], [[10, 10], 1], [[4, -1], 0], [[20, 10], 184756], [[50, 25], 126410606437752]];
const ERRORS: unknown[][] = [[-1, 0]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
