# AURI-CANARY-d07ae44e-2417-5637-8b12-d5b7ec49bb59
import copy
import unittest

from solution import binaris_kereses

CASES = [(([1, 3, 5, 7], 5), 2), (([1, 3], 4), -1)]


def _call(args: tuple) -> str:
    return "binaris_kereses(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(binaris_kereses(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
