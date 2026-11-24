# AURI-CANARY-0e0bd4b4-a97e-5c10-9243-874a3884f623
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import prim

CASES = [((0,), False),
 ((1,), False),
 ((2,), True),
 ((-7,), False),
 ((97,), True),
 ((91,), False),
 ((7919,), True),
 ((1000003,), True),
 ((1000001,), False)]


def _call(args: tuple) -> str:
    return "prim(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(prim(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
