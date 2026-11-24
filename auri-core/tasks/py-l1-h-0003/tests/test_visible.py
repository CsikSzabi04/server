# AURI-CANARY-9cd25317-5484-5122-92fc-a966adb0b6d2
import builtins
import copy
import unittest

from solution import szamrendszerbol

CASES = [(('ff', 16), 255), (('101', 2), 5)]
ERRORS = [(('', 10), 'ValueError')]


def _call(args: tuple) -> str:
    return "szamrendszerbol(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
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
