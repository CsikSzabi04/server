// AURI-CANARY-a605c37e-b060-5b86-9596-9ab6e7c933e8
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamjegyosszeg } from '../solution.ts';

const f = szamjegyosszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamjegyosszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[123], 6], [[0], 0]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
