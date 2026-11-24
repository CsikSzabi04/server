// AURI-CANARY-80029ac3-0715-5ac6-b026-3320dd631be4
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { szamrendszerbol } from '../solution.ts';

const f = szamrendszerbol as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `szamrendszerbol(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["FF", 16], 255], [["z", 36], 35], [["0", 2], 0], [["777", 8], 511], [["10", 36], 36]];
const ERRORS: unknown[][] = [["", 10], ["12", 2], ["-5", 10], ["1 0", 10], ["0x1f", 16], ["1_0", 10], ["5", 1], ["5", 37]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
