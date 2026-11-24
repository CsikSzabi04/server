# AURI-CANARY-fa520df1-be4f-5f6d-b774-85683bce9944
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import elofordulas

CASES = [(([0, 0, 0], 0), 3), (([1, 2, 3], 4), 0), (([-1, 1, -1], -1), 2)]


def _call(args: tuple) -> str:
    return "elofordulas(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(elofordulas(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
