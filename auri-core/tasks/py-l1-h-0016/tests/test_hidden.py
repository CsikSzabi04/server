# AURI-CANARY-d30b9687-12b9-5a93-9128-4fb6dd14c4da
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import collatz_lepesek

CASES = [((2,), 1), ((7,), 16), ((27,), 111), ((12,), 9)]
ERRORS = [((0,), 'ValueError'), ((-3,), 'ValueError')]


def _call(args: tuple) -> str:
    return "collatz_lepesek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(collatz_lepesek(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                collatz_lepesek(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
