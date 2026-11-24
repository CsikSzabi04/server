// AURI-CANARY-d72664bf-568f-53b9-96d7-bb23a6ca7731
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { leghosszabbNovekvo } from '../solution.ts';

const f = leghosszabbNovekvo as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `leghosszabbNovekvo(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[5, 4, 3]], 1], [[[1, 1, 1]], 1], [[[1, 2, 2, 3, 4, 5]], 4], [[[-3, -2, -1, 0]], 4], [[[7]], 1]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
