// AURI-CANARY-1a4500b2-6341-5371-b794-a2055a0e04bf
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mozgoAtlag } from '../solution.ts';

const f = mozgoAtlag as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `mozgoAtlag(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, 2, 3, 4], 2], [1.5, 2.5, 3.5]], [[[1, 2], 3], []]];
const ERRORS: unknown[][] = [[[1], 0]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
