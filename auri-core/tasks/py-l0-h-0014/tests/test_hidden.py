# AURI-CANARY-4c23fd78-6c31-5e53-bcd8-860b2871a9a4
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import atlagon_feluli

CASES = [(([5, 5, 5],), []), (([10, 0, 0],), [10]), (([-1, -2, 3],), [3]), (([1, 2],), [2])]


def _call(args: tuple) -> str:
    return "atlagon_feluli(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(atlagon_feluli(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
