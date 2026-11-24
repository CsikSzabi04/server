# AURI-CANARY-fcec98ed-c3c0-5d8b-b4c0-bc2ac0a485d6
import builtins
import copy
import unittest

from solution import matrix_forgat

CASES = [(([[1, 2], [3, 4]],), [[3, 1], [4, 2]]), (([],), [])]
ERRORS = [(([[1, 2], [3]],), 'ValueError')]


def _call(args: tuple) -> str:
    return "matrix_forgat(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(matrix_forgat(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                matrix_forgat(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
