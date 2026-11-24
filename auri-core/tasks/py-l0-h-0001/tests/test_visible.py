# AURI-CANARY-3be1190c-5458-5d2c-8b59-a1d5433055c0
import copy
import unittest

from solution import paratlan_osszeg

CASES = [(([1, 2, 3],), 4), (([],), 0)]


def _call(args: tuple) -> str:
    return "paratlan_osszeg(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(paratlan_osszeg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
