// AURI-CANARY-ff4d6d19-f32f-5de8-8669-32b8e51c8004
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { statisztika } from '../solution.ts';

const f = statisztika as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `statisztika(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["Alma 12!"], {"betu": 4, "szamjegy": 2, "szokoz": 1, "egyeb": 1}]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
