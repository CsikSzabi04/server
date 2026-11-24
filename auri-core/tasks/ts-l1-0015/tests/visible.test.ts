// AURI-CANARY-7d8c4ff5-5e0e-58f0-8f6a-91ef8b761cac
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { idotartamMp } from '../solution.ts';

const f = idotartamMp as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `idotartamMp(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["1h 30m"], 5400], [["45s"], 45]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
