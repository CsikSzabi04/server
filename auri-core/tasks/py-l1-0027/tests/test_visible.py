# AURI-CANARY-8e6bc047-3624-5673-839e-79ec01a97caa
import copy
import unittest

from solution import sortores

CASES = [(('alma körte szilva', 10), ['alma körte', 'szilva'])]


def _call(args: tuple) -> str:
    return "sortores(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(sortores(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
