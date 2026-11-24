// AURI-CANARY-9cfed738-9ee5-5b19-b178-f85b6aa4cf92
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { honapNapjai } from '../solution.ts';

const f = honapNapjai as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `honapNapjai(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[2023, 2], 28], [[1900, 2], 28], [[2000, 2], 29], [[2023, 4], 30], [[2023, 12], 31], [[2023, 11], 30], [[2023, 7], 31]];
const ERRORS: unknown[][] = [[2023, 0], [2023, 13]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
