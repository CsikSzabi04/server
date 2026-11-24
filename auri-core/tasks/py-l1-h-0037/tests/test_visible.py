# AURI-CANARY-f77963f6-172d-543e-aa1c-c364aafb8467
import copy
import unittest

from solution import egyensuly_index

CASES = [(([1, 7, 3, 6, 5, 6],), 3), (([1, 2, 3],), -1)]


def _call(args: tuple) -> str:
    return "egyensuly_index(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(egyensuly_index(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
