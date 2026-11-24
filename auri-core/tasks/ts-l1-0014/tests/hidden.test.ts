// AURI-CANARY-dfee3b81-f60f-5bc7-9787-b895a9abddeb
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tajErvenyes } from '../solution.ts';

const f = tajErvenyes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `tajErvenyes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["123 456 788"], true], [["987654322"], true], [["000000000"], true], [["12345678"], false], [["1234567888"], false], [["12345678a"], false], [["123-456-788"], false], [[""], false], [["123  456 788"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
