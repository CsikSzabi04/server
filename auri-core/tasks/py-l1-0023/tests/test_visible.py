# AURI-CANARY-0e0bd4b4-a97e-5c10-9243-874a3884f623
import copy
import unittest

from solution import prim

CASES = [((7,), True), ((8,), False)]


def _call(args: tuple) -> str:
    return "prim(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(prim(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
