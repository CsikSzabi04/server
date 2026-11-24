// AURI-CANARY-904ec899-da53-5876-b93c-95fd885a3a99
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { huszar } from '../solution.ts';

const f = huszar as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `huszar(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["b1"], ["a3", "c3", "d2"]], [["a1"], ["b3", "c2"]]];
const ERRORS: unknown[][] = [["i1"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
