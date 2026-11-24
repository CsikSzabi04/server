# AURI-CANARY-7cbd345c-f908-554a-94ad-a8efe0595472
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import pangramma

CASES = [(('',), False),
 (('ABCDEFGHIJKLMNOPQRSTUVWXYZ',), True),
 (('abcdefghijklmnopqrstuvwxy',), False),
 (('Pack my box with five dozen liquor jugs.',), True),
 (('árvíztűrő tükörfúrógép',), False)]


def _call(args: tuple) -> str:
    return "pangramma(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(pangramma(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
