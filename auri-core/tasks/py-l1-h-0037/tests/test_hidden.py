# AURI-CANARY-f77963f6-172d-543e-aa1c-c364aafb8467
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import egyensuly_index

CASES = [(([],), -1),
 (([5],), 0),
 (([2, 1, -1],), 0),
 (([0, 0, 0],), 0),
 (([1, -1, 4],), 2),
 (([-1, -1, -1, 0, 1, 1],), 0)]


def _call(args: tuple) -> str:
    return "egyensuly_index(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(egyensuly_index(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
