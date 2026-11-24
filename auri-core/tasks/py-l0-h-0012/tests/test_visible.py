# AURI-CANARY-ae11b12d-862c-57f4-af81-d3c99dae5b7a
import copy
import unittest

from solution import kozos

CASES = [(([1, 2, 3, 2], [2, 3, 4]), [2, 3])]


def _call(args: tuple) -> str:
    return "kozos(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kozos(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
