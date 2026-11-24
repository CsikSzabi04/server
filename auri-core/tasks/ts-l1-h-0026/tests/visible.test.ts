// AURI-CANARY-b8387c55-c2d0-50f6-8730-8ee6c84893d2
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { csvSor } from '../solution.ts';

const f = csvSor as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `csvSor(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["a,b,c"], ["a", "b", "c"]], [["\"x,y\",z"], ["x,y", "z"]]];
const ERRORS: unknown[][] = [["\"abc"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
