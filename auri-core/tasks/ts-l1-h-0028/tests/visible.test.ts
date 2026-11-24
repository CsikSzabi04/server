// AURI-CANARY-f2691306-b151-5e76-8b30-ea8b701e81d7
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { racsUt } from '../solution.ts';

const f = racsUt as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `racsUt(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[["..", ".."]], 2], [[["#."]], -1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
