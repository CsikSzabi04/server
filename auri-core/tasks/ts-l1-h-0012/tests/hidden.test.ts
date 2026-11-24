// AURI-CANARY-8a1f55bf-b062-5097-8c2d-3ccfde5e65fc
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { luhn } from '../solution.ts';

const f = luhn as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `luhn(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["7992 7398 713"], true], [["059"], true], [["0"], false], [[" 0"], false], [["0000 0"], true], [["055-444"], false], [["59"], true], [["8a"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
