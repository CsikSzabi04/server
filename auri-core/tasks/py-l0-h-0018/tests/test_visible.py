# AURI-CANARY-18275bc9-b968-5e81-b84b-c8dde2ef2452
import builtins
import copy
import unittest

from solution import ido_formatum

CASES = [((3661,), '01:01:01'), ((0,), '00:00:00')]
ERRORS = [((-1,), 'ValueError')]


def _call(args: tuple) -> str:
    return "ido_formatum(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ido_formatum(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                ido_formatum(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
