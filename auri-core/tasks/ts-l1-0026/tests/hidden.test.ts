// AURI-CANARY-a4d9683d-9188-5f7a-8ba3-fc3218621614
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { telefonszam } from '../solution.ts';

const f = telefonszam as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `telefonszam(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["+36301234567"], "+36301234567"], [["36-20-765-4321"], "+36207654321"], [["(06) 70/111-2222"], "+36701112222"], [["06301234567"], "+36301234567"]];
const ERRORS: unknown[][] = [[""], ["30 123 4567"], ["06 30 123 456"], ["+3630123456a"], ["+36 30 123 45678"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
