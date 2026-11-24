// AURI-CANARY-71415bf7-1b3e-58ac-835b-263d42d7d00d
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hosszSzerint } from '../solution.ts';

const f = hosszSzerint as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hosszSzerint(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[["a", "bb", "c"]], {"1": ["a", "c"], "2": ["bb"]}]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
