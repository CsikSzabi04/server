// AURI-CANARY-7d3a29c7-565b-547e-8165-a1a626e49ff7
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { minErmek } from '../solution.ts';

const f = minErmek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `minErmek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[11, [1, 2, 5]], 3], [[3, [2]], -1]];
const ERRORS: unknown[][] = [[-1, [1]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
