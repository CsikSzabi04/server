// AURI-CANARY-a4d9683d-9188-5f7a-8ba3-fc3218621614
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { telefonszam } from '../solution.ts';

const f = telefonszam as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `telefonszam(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["06 30 123 4567"], "+36301234567"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
