# AURI-CANARY-6fbf813d-34b7-51eb-8b67-0b4e98de2849
import copy
import unittest

from solution import idotartam_szoveg

CASES = [((3661,), '1 óra 1 perc 1 másodperc'), ((0,), '0 másodperc')]


def _call(args: tuple) -> str:
    return "idotartam_szoveg(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(idotartam_szoveg(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
