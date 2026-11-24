// AURI-CANARY-23919316-df3f-540d-a8a5-ca3acdcd5244
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kozos } from '../solution.ts';

const f = kozos as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kozos(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[], [1]], []], [[[1, 1, 1], [1]], [1]], [[[3, 2, 1], [1, 2, 3]], [3, 2, 1]], [[[5], []], []]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
