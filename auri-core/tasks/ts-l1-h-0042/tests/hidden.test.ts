// AURI-CANARY-d436fa57-5dbf-5f5a-b73e-0d63642c9758
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { modusz } from '../solution.ts';

const f = modusz as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `modusz(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[5]], 5], [[[3, 1, 3, 1]], 1], [[[-1, -1, 2, 2, 2]], 2], [[[4, 4, -4, -4]], -4], [[[7, 8, 9]], 7]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
