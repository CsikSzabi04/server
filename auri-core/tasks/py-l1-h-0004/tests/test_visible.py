# AURI-CANARY-2a19792a-5c26-5fdf-a52b-2a54533878ae
import copy
import unittest

from solution import betu_gyakorisag

CASES = [(('Alma',), {'a': 2, 'l': 1, 'm': 1}), (('',), {})]


def _call(args: tuple) -> str:
    return "betu_gyakorisag(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(betu_gyakorisag(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
