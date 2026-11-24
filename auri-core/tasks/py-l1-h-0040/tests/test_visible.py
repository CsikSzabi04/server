# AURI-CANARY-9ea9c482-407f-5ea8-bc8d-ae0f87bd4a84
import builtins
import copy
import unittest

from solution import hex_szin

CASES = [(('#ff8800',), [255, 136, 0]), (('#f80',), [255, 136, 0])]
ERRORS = [(('ff8800',), 'ValueError')]


def _call(args: tuple) -> str:
    return "hex_szin(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(hex_szin(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                hex_szin(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
