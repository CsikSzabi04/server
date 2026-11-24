// AURI-CANARY-45e29d38-377a-57fe-8671-b9cf6d53d228
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matrixSzorzas } from '../solution.ts';

const f = matrixSzorzas as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `matrixSzorzas(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[[[1, 2, 3]], [[1], [2], [3]]], [[14]]], [[[[2]], [[3]]], [[6]]], [[[[1], [2]], [[3, 4]]], [[3, 4], [6, 8]]], [[[[1, 0], [0, 1]], [[5, -1], [2, 7]]], [[5, -1], [2, 7]]]];
const ERRORS: unknown[][] = [[[[1, 2]], [[1, 2]]], [[], [[1]]], [[[1]], []]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
