# AURI-CANARY-64d05c92-5a1f-595b-bcbd-6bd664b59960
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import celsius_fahrenheit

CASES = [((-40,), -40.0), ((37,), 98.6), ((36.6,), 97.9), ((-273.15,), -459.7)]


def _call(args: tuple) -> str:
    return "celsius_fahrenheit(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(celsius_fahrenheit(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
