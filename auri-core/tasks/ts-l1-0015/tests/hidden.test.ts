// AURI-CANARY-7d8c4ff5-5e0e-58f0-8f6a-91ef8b761cac
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { idotartamMp } from '../solution.ts';

const f = idotartamMp as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `idotartamMp(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["2h"], 7200], [["1h 1m 1s"], 3661], [["90m"], 5400], [["0s"], 0], [["10m 5s"], 605], [["1h 5s"], 3605]];
const ERRORS: unknown[][] = [[""], ["1x"], ["30m 1h"], ["h"], ["1h 1h"], ["1h30m"]];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
