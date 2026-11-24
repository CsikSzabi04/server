// AURI-CANARY-58219427-7a49-5c5c-bcff-c0c4afa9bdbc
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { betuGyakorisag } from '../solution.ts';

const f = betuGyakorisag as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `betuGyakorisag(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["Öt ökör!"], {"ö": 3, "t": 1, "k": 1, "r": 1}], [["123 ..."], {}], [["aA aA"], {"a": 4}]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
