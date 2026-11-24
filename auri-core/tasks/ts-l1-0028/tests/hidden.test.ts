// AURI-CANARY-f077ffbc-0ac3-5102-9aef-2a5b4adefa5b
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { maganhangzok } from '../solution.ts';

const f = maganhangzok as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `maganhangzok(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["ÁRVÍZTŰRŐ TÜKÖRFÚRÓGÉP"], 9], [["xyz"], 0], [["aeiou"], 5], [["Öböl"], 2]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
