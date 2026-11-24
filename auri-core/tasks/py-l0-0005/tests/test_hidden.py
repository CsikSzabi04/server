# AURI-CANARY-80f401a2-d116-56f1-83e5-d80695bcc180
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szamjegyosszeg

CASES = [((-456,), 15), ((9999,), 36), ((1000000000000,), 1)]


def _call(args: tuple) -> str:
    return "szamjegyosszeg(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szamjegyosszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
