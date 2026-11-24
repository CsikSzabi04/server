// AURI-CANARY-69ffcce6-acd4-5f9f-b5a4-da272b68372c
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hexSzin } from '../solution.ts';

const f = hexSzin as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `hexSzin(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["#000000"], [0, 0, 0]], [["#FFFFFF"], [255, 255, 255]], [["#1a2B3c"], [26, 43, 60]], [["#abc"], [170, 187, 204]]];
const ERRORS: unknown[][] = [["ff8800"], ["#ff880"], ["#ggg"], [""], ["#ff88001"], ["#ff8800\n"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
