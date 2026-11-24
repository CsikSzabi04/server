# AURI-CANARY-ae11b12d-862c-57f4-af81-d3c99dae5b7a
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import kozos

CASES = [(([], [1]), []), (([1, 1, 1], [1]), [1]), (([3, 2, 1], [1, 2, 3]), [3, 2, 1]), (([5], []), [])]


def _call(args: tuple) -> str:
    return "kozos(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kozos(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
