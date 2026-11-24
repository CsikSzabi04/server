// AURI-CANARY-1a2c84ca-7892-5d7f-9af4-15f71a6c8d6a
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { anagramma } from '../solution.ts';

const f = anagramma as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `anagramma(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["Listen", "Silent"], true], [["alma", "körte"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
