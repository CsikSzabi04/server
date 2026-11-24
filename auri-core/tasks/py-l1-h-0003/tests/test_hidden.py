# AURI-CANARY-9cd25317-5484-5122-92fc-a966adb0b6d2
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import szamrendszerbol

CASES = [(('FF', 16), 255), (('z', 36), 35), (('0', 2), 0), (('777', 8), 511), (('10', 36), 36)]
ERRORS = [(('', 10), 'ValueError'),
 (('12', 2), 'ValueError'),
 (('-5', 10), 'ValueError'),
 (('1 0', 10), 'ValueError'),
 (('0x1f', 16), 'ValueError'),
 (('1_0', 10), 'ValueError'),
 (('5', 1), 'ValueError'),
 (('5', 37), 'ValueError')]


def _call(args: tuple) -> str:
    return "szamrendszerbol(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szamrendszerbol(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                szamrendszerbol(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
