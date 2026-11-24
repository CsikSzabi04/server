// AURI-CANARY-560f1de0-5f80-53de-8269-51bd1f0a47db
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { palindrom } from '../solution.ts';

const f = palindrom as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `palindrom(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], true], [["Géza, kék az ég!"], true], [["Ab1ba"], true], [["ége"], false], [["12321"], true], [["12 3"], false], [["!!!"], true]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
