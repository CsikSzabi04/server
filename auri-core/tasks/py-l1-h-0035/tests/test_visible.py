# AURI-CANARY-db01f964-d922-5a99-88a6-2ec4fb05c377
import copy
import unittest

from solution import levenshtein

CASES = [(('kitten', 'sitting'), 3), (('', ''), 0)]


def _call(args: tuple) -> str:
    return "levenshtein(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(levenshtein(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
