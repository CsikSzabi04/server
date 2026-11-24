# AURI-CANARY-80fc3a0f-27a3-57eb-82b9-3490214d8931
import copy
import unittest

from solution import primek

CASES = [((10,), [2, 3, 5, 7])]


def _call(args: tuple) -> str:
    return "primek(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(primek(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
