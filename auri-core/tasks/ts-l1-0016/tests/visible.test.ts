// AURI-CANARY-31b45d03-56a8-54c8-9abb-00474dd1c4d8
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { idotartamSzoveg } from '../solution.ts';

const f = idotartamSzoveg as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `idotartamSzoveg(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[3661], "1 óra 1 perc 1 másodperc"], [[0], "0 másodperc"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
