# AURI-CANARY-27cb65f9-51da-5a06-98d4-0973c7279919
import copy
import unittest

from solution import szokoev

CASES = [((2024,), True), ((2023,), False)]


def _call(args: tuple) -> str:
    return "szokoev(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szokoev(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
