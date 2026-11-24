// AURI-CANARY-181474df-baad-5055-a0e6-774e14139208
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { csere } from '../solution.ts';

const f = csere as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `csere(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["AlMa"], "aLmA"], [[""], ""]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
