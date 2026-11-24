// AURI-CANARY-692ac689-7541-5642-9ef9-b195e913a2b3
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { faktorialis } from '../solution.ts';

const f = faktorialis as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `faktorialis(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[1], 1], [[10], 3628800], [[15], 1307674368000]];
const ERRORS: unknown[][] = [[-1], [-10]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
