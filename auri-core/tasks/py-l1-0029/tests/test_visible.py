# AURI-CANARY-d39871a9-abea-50ed-aa5e-c7cd2e5100fb
import copy
import unittest

from solution import telefonszam

CASES = [(('06 30 123 4567',), '+36301234567')]


def _call(args: tuple) -> str:
    return "telefonszam(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(telefonszam(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
