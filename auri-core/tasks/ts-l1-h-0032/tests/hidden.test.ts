// AURI-CANARY-cc49b68d-c4a9-5f28-b10b-f4447957bba2
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { csucsok } from '../solution.ts';

const f = csucsok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `csucsok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[5]], [0]], [[[3, 1, 2]], [0, 2]], [[[1, 1, 1]], []], [[[1, 2, 3, 4]], [3]], [[[2, 1, 3, 1, 4]], [0, 2, 4]], [[[1, 2, 2, 1]], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
