// AURI-CANARY-9e635f6e-3906-5e5b-8c23-1e2dd1147076
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { prim } from '../solution.ts';

const f = prim as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `prim(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[7], true], [[8], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
