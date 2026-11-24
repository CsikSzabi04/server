// AURI-CANARY-a5aac386-088d-5257-9b32-9be7ef00906b
// HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { caesar } from '../solution.ts';

const f = caesar as unknown as (...args: unknown[]) => unknown;
const call = (args: unknown[]): string => `caesar(${args.map((a) => JSON.stringify(a)).join(', ')})`;
const CASES: [unknown[], unknown][] = [[["xyz", 3], "abc"], [["abc", -1], "zab"], [["Hello, World!", 27], "Ifmmp, Xpsme!"], [["árvíz", 1], "áswía"], [["abc", 0], "abc"], [["", 5], ""], [["ABC", -27], "ZAB"]];
const ERRORS: unknown[][] = [];

for (const [args, want] of CASES) {
  test(call(args), () => assert.deepEqual(f(...structuredClone(args)), want, call(args)));
}
for (const args of ERRORS) {
  test(`hiba: ${call(args)}`, () => assert.throws(() => f(...structuredClone(args)), RangeError, call(args)));
}
