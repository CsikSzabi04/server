# AURI-CANARY-27cb65f9-51da-5a06-98d4-0973c7279919
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szokoev

CASES = [((1900,), False), ((2000,), True), ((2100,), False), ((1996,), True)]


def _call(args: tuple) -> str:
    return "szokoev(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szokoev(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
