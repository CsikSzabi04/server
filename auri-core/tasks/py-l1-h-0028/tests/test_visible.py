# AURI-CANARY-5496f464-07ef-5052-bf74-1ea1173273f3
import copy
import unittest

from solution import racs_ut

CASES = [((['..', '..'],), 2), ((['#.'],), -1)]


def _call(args: tuple) -> str:
    return "racs_ut(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(racs_ut(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
