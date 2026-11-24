// AURI-CANARY-0f4db97b-d067-546a-9695-8ae293bc3394
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { negyzetosszeg } from '../solution.ts';

const f = negyzetosszeg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `negyzetosszeg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[1], 1], [[10], 385], [[-5], 0], [[100], 338350]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
