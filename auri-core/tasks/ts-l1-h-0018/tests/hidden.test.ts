// AURI-CANARY-481f6c97-a709-5e95-8030-89c435a38c94
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pangramma } from '../solution.ts';

const f = pangramma as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `pangramma(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], false], [["ABCDEFGHIJKLMNOPQRSTUVWXYZ"], true], [["abcdefghijklmnopqrstuvwxy"], false], [["Pack my box with five dozen liquor jugs."], true], [["árvíztűrő tükörfúrógép"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
