# AURI-CANARY-6ce2a96c-718b-52ed-9383-7b71dc575559
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import min_ermek

CASES = [((0, [1]), 0),
 ((6, [1, 3, 4]), 2),
 ((7, [2, 4]), -1),
 ((100, [1, 5, 10, 25, 50]), 2),
 ((63, [1, 5, 10, 21, 25]), 3),
 ((1, []), -1)]
ERRORS = [((-1, [1]), 'ValueError')]


def _call(args: tuple) -> str:
    return "min_ermek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(min_ermek(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                min_ermek(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
