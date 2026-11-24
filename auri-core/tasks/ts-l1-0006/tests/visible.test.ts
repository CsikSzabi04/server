// AURI-CANARY-6c95c76a-3702-5ecb-8c1e-b8c7f53c286d
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { rleKodol } from '../solution.ts';

const f = rleKodol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `rleKodol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["aaabcc"], "3a1b2c"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
