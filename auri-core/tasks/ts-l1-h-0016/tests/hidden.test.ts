// AURI-CANARY-2b0f25af-3993-593e-891d-6dd49a43d166
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collatzLepesek } from '../solution.ts';

const f = collatzLepesek as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `collatzLepesek(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[[2], 1], [[7], 16], [[27], 111], [[12], 9]];
const ERRORS: unknown[][] = [[0], [-3]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
