// AURI-CANARY-05fc9fbd-09e4-57e4-be0a-0afad7f4df7f
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szigetek } from '../solution.ts';

const f = szigetek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szigetek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[["#..", "..#"]], 2], [[[]], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
