# AURI-CANARY-c5e0444b-461a-55fb-84d8-80fa89ead877
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import pascal_sor

CASES = [((1,), [1, 1]), ((2,), [1, 2, 1]), ((10,), [1, 10, 45, 120, 210, 252, 210, 120, 45, 10, 1])]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "pascal_sor(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(pascal_sor(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                pascal_sor(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
