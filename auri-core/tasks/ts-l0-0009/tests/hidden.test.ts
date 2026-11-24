// AURI-CANARY-7ab287f2-ada5-50d5-8889-9fe53e377e5f
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { nagybetusSzavak } from '../solution.ts';

const f = nagybetusSzavak as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `nagybetusSzavak(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[""], []], [["Árvíz és Öböl"], ["Árvíz", "Öböl"]], [["1Alma Bé"], ["Bé"]], [["ALMA körte"], ["ALMA"]]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
