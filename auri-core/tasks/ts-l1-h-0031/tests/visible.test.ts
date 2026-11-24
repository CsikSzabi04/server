// AURI-CANARY-ab9d945c-9611-573a-a611-19477961c997
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matrixForgat } from '../solution.ts';

const f = matrixForgat as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `matrixForgat(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[[1, 2], [3, 4]]], [[3, 1], [4, 2]]], [[[]], []]];
const ERRORS: unknown[][] = [[[[1, 2], [3]]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
