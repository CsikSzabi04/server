# AURI-CANARY-b2ae44a1-1b79-54d0-9c58-a30741c61832
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import modusz

CASES = [(([5],), 5), (([3, 1, 3, 1],), 1), (([-1, -1, 2, 2, 2],), 2), (([4, 4, -4, -4],), -4), (([7, 8, 9],), 7)]


def _call(args: tuple) -> str:
    return "modusz(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(modusz(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
