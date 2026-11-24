// AURI-CANARY-904ec899-da53-5876-b93c-95fd885a3a99
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { huszar } from '../solution.ts';

const f = huszar as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `huszar(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["d4"], ["b3", "b5", "c2", "c6", "e2", "e6", "f3", "f5"]], [["h8"], ["f7", "g6"]], [["g1"], ["e2", "f3", "h3"]]];
const ERRORS: unknown[][] = [["i1"], ["a9"], ["A1"], [""], ["a10"], ["a0"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
