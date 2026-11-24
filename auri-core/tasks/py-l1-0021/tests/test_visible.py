# AURI-CANARY-f0bd89d7-2749-5f0c-adad-a07a7ea32ff4
import copy
import unittest

from solution import forgat

CASES = [(([1, 2, 3, 4], 1), [4, 1, 2, 3])]


def _call(args: tuple) -> str:
    return "forgat(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(forgat(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
