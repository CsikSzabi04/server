# AURI-CANARY-e1c4bca5-d440-5835-8842-0b701b506ffc
import copy
import unittest

from solution import tokeletes

CASES = [((6,), True), ((8,), False)]


def _call(args: tuple) -> str:
    return "tokeletes(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(tokeletes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
