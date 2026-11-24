# AURI-CANARY-629c0c9a-1b1c-5238-b07c-b21c22c89e5e
import copy
import unittest

from solution import romai_ertek

CASES = [(('XIV',), 14), (('MCMXCIV',), 1994)]


def _call(args: tuple) -> str:
    return "romai_ertek(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(romai_ertek(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
