# AURI-CANARY-133e53f7-598a-5318-b3cb-721ca4c3ef3a
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import rle_kodol

CASES = [(('',), ''), (('a',), '1a'), (('aaaaaaaaaaaa',), '12a'), (('abab',), '1a1b1a1b'), (('őőű  ',), '2ő1ű2 ')]


def _call(args: tuple) -> str:
    return "rle_kodol(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(rle_kodol(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
