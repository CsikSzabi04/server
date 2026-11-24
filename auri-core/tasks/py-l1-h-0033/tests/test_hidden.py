# AURI-CANARY-e6ad6851-b7c7-5783-aeae-03d6edfacdf1
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import elso_egyedi

CASES = [(('',), None), (('x',), 'x'), (('aA',), 'a'), (('kakukk',), 'a'), (('abcabcd',), 'd'), (('őrölő',), 'r')]


def _call(args: tuple) -> str:
    return "elso_egyedi(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(elso_egyedi(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
