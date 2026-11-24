# AURI-CANARY-cd4c9e7f-e4e0-5def-be83-9ce69f7d0623
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import ezres_tagolas

CASES = [((999,), '999'),
 ((1000,), '1 000'),
 ((-1234,), '-1 234'),
 ((-5,), '-5'),
 ((100000,), '100 000'),
 ((12345678901,), '12 345 678 901')]


def _call(args: tuple) -> str:
    return "ezres_tagolas(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ezres_tagolas(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
