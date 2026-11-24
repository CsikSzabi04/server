# AURI-CANARY-e8ae753a-da02-51be-9e5e-50975be794bb
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import masodik_legnagyobb

CASES = [(([],), None), (([1],), None), (([-1, -2],), -2), (([1, 2, 3, 4, 5],), 4), (([10, 10, 9, 9],), 9)]


def _call(args: tuple) -> str:
    return "masodik_legnagyobb(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(masodik_legnagyobb(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
