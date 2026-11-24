// AURI-CANARY-3a555cbc-9406-50b1-9d6b-ba6a33020d9f
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { romaiErtek } from '../solution.ts';

const f = romaiErtek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `romaiErtek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["XIV"], 14], [["MCMXCIV"], 1994]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
