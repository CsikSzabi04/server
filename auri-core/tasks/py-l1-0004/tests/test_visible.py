# AURI-CANARY-7029c79e-5c99-5446-9c30-d345adc67520
import copy
import unittest

from solution import palindrom

CASES = [(('Indul a görög aludni',), True), (('alma',), False)]


def _call(args: tuple) -> str:
    return "palindrom(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(palindrom(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
