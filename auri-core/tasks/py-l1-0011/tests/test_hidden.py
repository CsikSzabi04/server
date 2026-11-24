# AURI-CANARY-49536514-79da-5829-b792-d05fcb8358b8
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import osszefesul

CASES = [(([], []), []), (([], [1]), [1]), (([1, 1], [1]), [1, 1, 1]), (([-5, 0], [-6, 10]), [-6, -5, 0, 10])]


def _call(args: tuple) -> str:
    return "osszefesul(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(osszefesul(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
