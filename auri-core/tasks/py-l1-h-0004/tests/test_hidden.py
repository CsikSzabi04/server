# AURI-CANARY-2a19792a-5c26-5fdf-a52b-2a54533878ae
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import betu_gyakorisag

CASES = [(('Öt ökör!',), {'ö': 3, 't': 1, 'k': 1, 'r': 1}), (('123 ...',), {}), (('aA aA',), {'a': 4})]


def _call(args: tuple) -> str:
    return "betu_gyakorisag(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(betu_gyakorisag(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
