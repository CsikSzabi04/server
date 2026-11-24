// AURI-CANARY-aa20550e-067d-57a4-9a66-1b0e798a618e
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { transzponal } from '../solution.ts';

const f = transzponal as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `transzponal(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[]], []], [[[[1]]], [[1]]], [[[[1, 2]]], [[1], [2]]], [[[[1], [2]]], [[1, 2]]]];
const ERRORS: unknown[][] = [[[[1, 2], [3]]]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
