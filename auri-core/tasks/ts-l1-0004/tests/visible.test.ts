// AURI-CANARY-f5cb77f5-b3c3-567f-a871-56ebf8e35f08
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { darabol } from '../solution.ts';

const f = darabol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `darabol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4, 5], 2], [[1, 2], [3, 4], [5]]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
