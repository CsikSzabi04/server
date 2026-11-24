# AURI-CANARY-4c23fd78-6c31-5e53-bcd8-860b2871a9a4
import copy
import unittest

from solution import atlagon_feluli

CASES = [(([1, 2, 3, 4],), [3, 4]), (([],), [])]


def _call(args: tuple) -> str:
    return "atlagon_feluli(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(atlagon_feluli(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
