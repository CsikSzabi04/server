// AURI-CANARY-2d35d666-1f03-5f1c-bd71-5061d8eb1cdc
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { paratlanOsszeg } from '../solution.ts';

const f = paratlanOsszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `paratlanOsszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[-3, -2, 5]], 2], [[[2, 4, 6]], 0], [[[7]], 7], [[[-1, -1]], -2]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
