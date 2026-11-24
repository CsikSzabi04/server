// AURI-CANARY-58219427-7a49-5c5c-bcff-c0c4afa9bdbc
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { betuGyakorisag } from '../solution.ts';

const f = betuGyakorisag as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `betuGyakorisag(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["Alma"], {"a": 2, "l": 1, "m": 1}], [[""], {}]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
