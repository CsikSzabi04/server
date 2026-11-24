// AURI-CANARY-85358d24-0e4a-5816-8d23-2cf60074854d
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { zarojelek } from '../solution.ts';

const f = zarojelek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `zarojelek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["([]{})"], true], [["(]"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
