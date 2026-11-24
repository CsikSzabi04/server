# AURI-CANARY-a3249e12-2640-5f04-988a-740ce7a26a09
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import faktorialis

CASES = [((1,), 1), ((10,), 3628800), ((15,), 1307674368000)]
ERRORS = [((-1,), 'ValueError'), ((-10,), 'ValueError')]


def _call(args: tuple) -> str:
    return "faktorialis(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(faktorialis(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                faktorialis(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
