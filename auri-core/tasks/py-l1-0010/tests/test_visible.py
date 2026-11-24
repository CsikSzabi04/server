# AURI-CANARY-319adfe0-2fec-5687-b7fa-4ba86e12eb92
import copy
import unittest

from solution import rle_dekodol

CASES = [(('3a1b2c',), 'aaabcc')]


def _call(args: tuple) -> str:
    return "rle_dekodol(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(rle_dekodol(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
