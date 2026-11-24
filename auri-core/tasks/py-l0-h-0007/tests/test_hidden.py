# AURI-CANARY-0e97ffe8-0973-5f10-a001-5832a1068249
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import haromszog

CASES = [((2, 2, 3), True), ((0, 1, 1), False), ((-3, 4, 5), False), ((10, 1, 1), False), ((1.5, 1.5, 2.9), True)]


def _call(args: tuple) -> str:
    return "haromszog(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(haromszog(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
