// AURI-CANARY-5b72fbd1-5ccf-5d62-86fd-db5b5093bff4
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { haromszog } from '../solution.ts';

const f = haromszog as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `haromszog(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[3, 4, 5], true], [[1, 2, 3], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
