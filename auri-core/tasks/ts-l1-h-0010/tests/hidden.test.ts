// AURI-CANARY-718c62d1-65c1-50a8-a62f-4d5ff1696d06
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ipv4Ervenyes } from '../solution.ts';

const f = ipv4Ervenyes as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `ipv4Ervenyes(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["0.0.0.0"], true], [["255.255.255.255"], true], [["01.2.3.4"], false], [["1.2.3"], false], [["1.2.3.4.5"], false], [["1.2..4"], false], [["1.2.3.-4"], false], [[" 1.2.3.4"], false], [["1.2.3.4a"], false], [["1000.1.1.1"], false]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
