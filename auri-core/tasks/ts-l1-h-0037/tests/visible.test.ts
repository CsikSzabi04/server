// AURI-CANARY-5d51b69d-2bb5-531c-84f8-0c7c39349b19
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { egyensulyIndex } from '../solution.ts';

const f = egyensulyIndex as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `egyensulyIndex(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 7, 3, 6, 5, 6]], 3], [[[1, 2, 3]], -1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
