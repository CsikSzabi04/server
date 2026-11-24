# AURI-CANARY-4031638c-818e-5560-bb7c-5b852e19d921
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import intervallumok

CASES = [(([[1, 2], [2, 3]],), [[1, 3]]),
 (([[5, 6], [1, 2]],), [[1, 2], [5, 6]]),
 (([[1, 10], [2, 3], [4, 5]],), [[1, 10]]),
 (([[3, 3]],), [[3, 3]]),
 (([[-5, -1], [-2, 0], [1, 1]],), [[-5, 0], [1, 1]])]
ERRORS = [(([[2, 1]],), 'ValueError'), (([[1, 2], [5, 4]],), 'ValueError')]


def _call(args: tuple) -> str:
    return "intervallumok(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(intervallumok(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                intervallumok(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
