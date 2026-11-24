// AURI-CANARY-f511e1f8-43cc-58b4-87b8-951d776e3409
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { terjedelem } from '../solution.ts';

const f = terjedelem as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `terjedelem(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[5]], 0], [[[-5, 5]], 10], [[[2, 2, 2]], 0], [[[-10, -3]], 7]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
