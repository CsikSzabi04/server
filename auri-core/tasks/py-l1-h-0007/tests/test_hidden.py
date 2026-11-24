# AURI-CANARY-766afb16-1347-57a4-b8ef-9024be4f3a20
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import mozgo_atlag

CASES = [(([1, 2, 4], 3), [2.33]),
 (([1, 2, 5, 1], 3), [2.67, 2.67]),
 (([5], 1), [5]),
 (([2, 4, 6, 8, 10], 5), [6]),
 (([1, 1, 2], 2), [1, 1.5])]
ERRORS = [(([1], 0), 'ValueError'), (([], -1), 'ValueError')]


def _call(args: tuple) -> str:
    return "mozgo_atlag(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(mozgo_atlag(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                mozgo_atlag(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
