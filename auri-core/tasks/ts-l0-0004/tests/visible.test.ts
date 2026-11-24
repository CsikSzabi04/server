// AURI-CANARY-233404da-e1f6-5ce8-8e49-7d049a346141
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { maxIndex } from '../solution.ts';

const f = maxIndex as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `maxIndex(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 5, 3]], 1], [[[]], -1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
