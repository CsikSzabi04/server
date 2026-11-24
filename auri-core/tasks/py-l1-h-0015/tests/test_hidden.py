# AURI-CANARY-e1c4bca5-d440-5835-8842-0b701b506ffc
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import tokeletes

CASES = [((28,), True),
 ((496,), True),
 ((8128,), True),
 ((1,), False),
 ((0,), False),
 ((-6,), False),
 ((12,), False),
 ((33550336,), True)]


def _call(args: tuple) -> str:
    return "tokeletes(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(tokeletes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
