# AURI-CANARY-a191db31-329c-590c-8ff8-dfd1eba2ddef
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import teljes_negyzet

CASES = [((0,), True),
 ((-4,), False),
 ((1000000,), True),
 ((999999,), False),
 ((1000000000000,), True),
 ((1000000000001,), False)]


def _call(args: tuple) -> str:
    return "teljes_negyzet(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(teljes_negyzet(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
