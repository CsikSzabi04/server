// AURI-CANARY-f33d6555-8c44-5dd8-bdec-12b36b23816b
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parosSzamok } from '../solution.ts';

const f = parosSzamok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `parosSzamok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4]], [2, 4]], [[[]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
