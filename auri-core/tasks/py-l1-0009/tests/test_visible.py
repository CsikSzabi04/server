# AURI-CANARY-133e53f7-598a-5318-b3cb-721ca4c3ef3a
import copy
import unittest

from solution import rle_kodol

CASES = [(('aaabcc',), '3a1b2c')]


def _call(args: tuple) -> str:
    return "rle_kodol(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(rle_kodol(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
