# AURI-CANARY-703a1a4f-276e-5814-8e39-ed114a5c29c3
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import darabol

CASES = [(([], 3), []),
 (([1, 2], 5), [[1, 2]]),
 (([1, 2, 3], 1), [[1], [2], [3]]),
 (([1, 2, 3, 4], 2), [[1, 2], [3, 4]])]
ERRORS = [(([1], 0), 'ValueError'), (([1], -2), 'ValueError')]


def _call(args: tuple) -> str:
    return "darabol(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(darabol(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                darabol(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
