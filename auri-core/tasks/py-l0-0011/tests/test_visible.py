# AURI-CANARY-db84fa3c-a13a-5624-a813-020d0e8fac75
import copy
import unittest

from solution import fizzbuzz

CASES = [((5,), ['1', '2', 'Fizz', '4', 'Buzz'])]


def _call(args: tuple) -> str:
    return "fizzbuzz(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(fizzbuzz(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
