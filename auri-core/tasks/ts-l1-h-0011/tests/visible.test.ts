// AURI-CANARY-955bf4bc-a70e-5dc6-9a8e-d76ca5049f58
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isbn10Ervenyes } from '../solution.ts';

const f = isbn10Ervenyes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `isbn10Ervenyes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["0-306-40615-2"], true], [["0-306-40615-3"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
