// AURI-CANARY-db9d8604-4d0e-5c08-a232-71d5e00d9284
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { median } from '../solution.ts';

const f = median as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `median(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[5]], 5], [[[10, -10]], 0], [[[1, 1, 1, 1]], 1], [[[-5, -1, -3]], -3], [[[0.5, 1.5]], 1.0], [[[1, 10, 2]], 2], [[[10, 2, 38, 23, 38, 23, 21]], 23]];
const ERRORS: unknown[][] = [[[]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
