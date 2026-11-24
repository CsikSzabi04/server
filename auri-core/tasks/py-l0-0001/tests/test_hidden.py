# AURI-CANARY-42363330-0e69-5a2c-b1e3-b28b4bd3a537
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import paros_szamok

CASES = [(([-2, -1, 0, 7],), [-2, 0]), (([5, 5, 6, 6],), [6, 6]), (([1, 3],), [])]


def _call(args: tuple) -> str:
    return "paros_szamok(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(paros_szamok(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
