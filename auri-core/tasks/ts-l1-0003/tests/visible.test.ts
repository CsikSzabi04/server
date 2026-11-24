// AURI-CANARY-90e057c9-65a3-5662-a737-1ff2dd6af0c5
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { romaiSzam } from '../solution.ts';

const f = romaiSzam as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `romaiSzam(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[14], "XIV"], [[1994], "MCMXCIV"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
