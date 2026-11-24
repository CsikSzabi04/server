// AURI-CANARY-9f644fa5-f819-5139-9baf-6abf092cd8af
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elofordulas } from '../solution.ts';

const f = elofordulas as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `elofordulas(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 1, 3], 1], 2], [[[], 5], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
