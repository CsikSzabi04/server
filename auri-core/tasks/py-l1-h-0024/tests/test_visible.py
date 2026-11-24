# AURI-CANARY-3380e876-a0bb-5a01-b389-a47c7cc227bb
import builtins
import copy
import unittest

from solution import honap_napjai

CASES = [((2024, 2), 29), ((2023, 1), 31)]
ERRORS = [((2023, 0), 'ValueError')]


def _call(args: tuple) -> str:
    return "honap_napjai(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(honap_napjai(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                honap_napjai(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
