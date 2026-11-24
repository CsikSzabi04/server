# AURI-CANARY-a8c3c770-f2df-5fe1-8ddc-6eac52f41405
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import max_index

CASES = [(([7, 7, 2],), 0), (([-3, -1, -2],), 1), (([0],), 0), (([1, 2, 3, 3],), 2)]


def _call(args: tuple) -> str:
    return "max_index(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(max_index(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
