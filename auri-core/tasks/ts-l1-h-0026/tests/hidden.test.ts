// AURI-CANARY-b8387c55-c2d0-50f6-8730-8ee6c84893d2
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { csvSor } from '../solution.ts';

const f = csvSor as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `csvSor(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], [""]], [["a,"], ["a", ""]], [[","], ["", ""]], [["\"mondd: \"\"szia\"\"\",2"], ["mondd: \"szia\"", "2"]], [["\"\",x"], ["", "x"]], [["egy, kettő"], ["egy", " kettő"]], [["\"a\""], ["a"]]];
const ERRORS: unknown[][] = [["\"abc"], ["\"a\"b,c"], ["a\"b"], ["\"a\"\""]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
