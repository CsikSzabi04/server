# AURI-CANARY-b125952b-42a0-51a4-b185-0020b7c2b34e
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import ket_osszeg

CASES = [(([3, 3], 6), [0, 1]),
 (([1, 2, 3, 4], 7), [2, 3]),
 (([], 0), None),
 (([0, 4, 3, 0], 0), [0, 3]),
 (([5, 1, 5], 10), [0, 2]),
 (([-1, 3, 4], 2), [0, 1]),
 (([1, 5, 2, 4], 6), [0, 1])]


def _call(args: tuple) -> str:
    return "ket_osszeg(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ket_osszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
