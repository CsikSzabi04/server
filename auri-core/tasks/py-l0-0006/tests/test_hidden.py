# AURI-CANARY-fde339dd-9997-5ec9-85dd-c359fd6feead
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szavak_szama

CASES = [(('  sok   szóköz  ',), 2), (('egy\tkettő\nhárom',), 3), (('szó',), 1)]


def _call(args: tuple) -> str:
    return "szavak_szama(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szavak_szama(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
