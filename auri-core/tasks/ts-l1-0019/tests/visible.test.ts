// AURI-CANARY-36faccdf-7890-55d9-9ce0-b99958b109e2
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pascalSor } from '../solution.ts';

const f = pascalSor as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `pascalSor(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[0], [1]], [[4], [1, 4, 6, 4, 1]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
