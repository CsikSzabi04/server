# AURI-CANARY-de864572-4bf2-5dec-b9d2-9456db8b961e
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import median

CASES = [(([5],), 5),
 (([10, -10],), 0),
 (([1, 1, 1, 1],), 1),
 (([-5, -1, -3],), -3),
 (([0.5, 1.5],), 1.0),
 (([1, 10, 2],), 2),
 (([10, 2, 38, 23, 38, 23, 21],), 23)]
ERRORS = [(([],), 'ValueError')]


def _call(args: tuple) -> str:
    return "median(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(median(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                median(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
