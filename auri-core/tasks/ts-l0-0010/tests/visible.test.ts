// AURI-CANARY-4bf3ed7f-410b-5d7c-bf25-c920496aeacd
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { atlag } from '../solution.ts';

const f = atlag as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `atlag(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4]], 2.5], [[[]], null]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
