# AURI-CANARY-d07ae44e-2417-5637-8b12-d5b7ec49bb59
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import binaris_kereses

CASES = [(([], 1), -1),
 (([2, 2, 2], 2), 0),
 (([1, 2, 2, 3], 2), 1),
 (([1], 1), 0),
 (([0, 2, 4, 6, 8, 10], 10), 5),
 (([1, 3], 0), -1)]


def _call(args: tuple) -> str:
    return "binaris_kereses(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(binaris_kereses(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
