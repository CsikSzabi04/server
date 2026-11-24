// AURI-CANARY-e1f22bb1-13cd-5d54-bcdc-6654975996e0
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kilapit } from '../solution.ts';

const f = kilapit as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kilapit(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[1, [2, [3, 4]], 5]], [1, 2, 3, 4, 5]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
