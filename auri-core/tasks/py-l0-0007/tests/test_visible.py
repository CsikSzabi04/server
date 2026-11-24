# AURI-CANARY-64d05c92-5a1f-595b-bcbd-6bd664b59960
import copy
import unittest

from solution import celsius_fahrenheit

CASES = [((0,), 32.0), ((100,), 212.0)]


def _call(args: tuple) -> str:
    return "celsius_fahrenheit(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(celsius_fahrenheit(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
