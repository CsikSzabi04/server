# AURI-CANARY-e8ae753a-da02-51be-9e5e-50975be794bb
import copy
import unittest

from solution import masodik_legnagyobb

CASES = [(([3, 1, 4, 4],), 3), (([5, 5],), None)]


def _call(args: tuple) -> str:
    return "masodik_legnagyobb(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(masodik_legnagyobb(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
