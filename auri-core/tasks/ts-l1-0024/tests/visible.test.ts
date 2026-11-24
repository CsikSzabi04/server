// AURI-CANARY-fd70fa72-93ae-5573-92d2-7a9f66cdea22
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { sortores } from '../solution.ts';

const f = sortores as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `sortores(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["alma körte szilva", 10], ["alma körte", "szilva"]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
