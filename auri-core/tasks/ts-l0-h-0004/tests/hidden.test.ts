// AURI-CANARY-5c308039-d9ee-5143-b432-4cacd1a9cbe6
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kozepso } from '../solution.ts';

const f = kozepso as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `kozepso(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], ""], [["x"], "x"], [["ab"], "ab"], [["árvíz"], "v"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
